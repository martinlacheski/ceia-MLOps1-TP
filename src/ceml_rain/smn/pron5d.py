"""Utilities to parse SMN 5-day numeric forecast files.

The SMN ``pron5d`` product is published as a ZIP with a TXT file inside.
Each station section contains 3-hourly rows with temperature, wind and
precipitation. This module keeps the parser dependency-free so it can run from
Airflow tasks, notebooks or simple scripts without requiring pandas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
import json
import re
from typing import Iterable
from urllib.request import urlopen
from zipfile import ZipFile


PRON5D_URL = "https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=pron5d"

MISIONES_STATIONS = frozenset(
    {
        "POSADAS_AERO",
        "IGUAZU_AERO",
        "OBERA_AERO",
        "BERNARDO_DE_IRIGOYEN_AERO",
    }
)

_MONTHS = {
    "ENE": 1,
    "FEB": 2,
    "MAR": 3,
    "ABR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AGO": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DIC": 12,
}

_FORECAST_ROW_RE = re.compile(
    r"^\s*"
    r"(?P<day>\d{1,2})/(?P<month>[A-Z]{3})/(?P<year>\d{4})\s+"
    r"(?P<hour>\d{1,2})Hs\.\s+"
    r"(?P<temperature>-?\d+(?:\.\d+)?)\s+"
    r"(?P<wind_direction>\d+)\s+\|\s+"
    r"(?P<wind_speed>\d+)\s+"
    r"(?P<precipitation>-?\d+(?:\.\d+)?)\s*$"
)


@dataclass(frozen=True)
class HourlyForecast:
    """One 3-hourly forecast row for a station."""

    station: str
    forecast_at: datetime
    temperature_c: float
    wind_direction_deg: int
    wind_speed_kmh: int
    precipitation_mm: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "station": self.station,
            "forecast_at": self.forecast_at.isoformat(),
            "temperature_c": self.temperature_c,
            "wind_direction_deg": self.wind_direction_deg,
            "wind_speed_kmh": self.wind_speed_kmh,
            "precipitation_mm": self.precipitation_mm,
        }


@dataclass(frozen=True)
class DailyPrecipitation:
    """Daily precipitation aggregate for a station."""

    station: str
    forecast_date: date
    precipitation_mm: float
    hours: int

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "station": self.station,
            "forecast_date": self.forecast_date.isoformat(),
            "precipitation_mm": self.precipitation_mm,
            "hours": self.hours,
        }


def fetch_pron5d_text(url: str = PRON5D_URL, timeout: int = 30) -> str:
    """Download the latest SMN pron5d ZIP and return the TXT content."""

    with urlopen(url, timeout=timeout) as response:
        payload = response.read()

    with ZipFile(BytesIO(payload)) as zip_file:
        txt_names = [name for name in zip_file.namelist() if name.lower().endswith(".txt")]
        if not txt_names:
            raise ValueError("SMN pron5d ZIP does not contain a TXT file")

        return zip_file.read(txt_names[0]).decode("utf-8-sig")


def parse_pron5d_text(text: str, stations: Iterable[str] | None = None) -> list[HourlyForecast]:
    """Parse an SMN pron5d TXT into hourly forecast records.

    Args:
        text: Raw TXT content extracted from the SMN ZIP.
        stations: Optional station allowlist. When omitted, all stations are parsed.
    """

    station_filter = {station.upper() for station in stations} if stations else None
    lines = text.splitlines()
    current_station: str | None = None
    records: list[HourlyForecast] = []

    for index, line in enumerate(lines):
        stripped = line.strip()

        if _is_station_header(stripped, lines, index):
            current_station = stripped
            continue

        if current_station is None:
            continue

        if station_filter is not None and current_station not in station_filter:
            continue

        row = _FORECAST_ROW_RE.match(line)
        if row is None:
            continue

        records.append(_record_from_match(current_station, row))

    return records


def parse_misiones_pron5d_text(text: str) -> list[HourlyForecast]:
    """Parse only the Misiones stations used by this project."""

    return parse_pron5d_text(text, stations=MISIONES_STATIONS)


def build_daily_misiones_forecast(text: str | None = None) -> list[DailyPrecipitation]:
    """Build the daily Misiones precipitation forecast from SMN pron5d.

    When ``text`` is provided the function is deterministic and does not touch
    the network, which is useful for tests. When omitted, it downloads the
    latest SMN pron5d ZIP.
    """

    source_text = text if text is not None else fetch_pron5d_text()
    records = parse_misiones_pron5d_text(source_text)
    return aggregate_daily_precipitation(records)


def aggregate_daily_precipitation(records: Iterable[HourlyForecast]) -> list[DailyPrecipitation]:
    """Aggregate 3-hourly precipitation rows by station and forecast date."""

    totals: dict[tuple[str, date], tuple[float, int]] = {}

    for record in records:
        key = (record.station, record.forecast_at.date())
        previous_total, previous_hours = totals.get(key, (0.0, 0))
        totals[key] = (previous_total + record.precipitation_mm, previous_hours + 1)

    return [
        DailyPrecipitation(
            station=station,
            forecast_date=forecast_date,
            precipitation_mm=round(total, 3),
            hours=hours,
        )
        for (station, forecast_date), (total, hours) in sorted(totals.items())
    ]


def daily_precipitation_to_jsonl(records: Iterable[DailyPrecipitation]) -> str:
    """Serialize daily precipitation records as JSON Lines.

    JSONL is convenient for Airflow tasks and MinIO because it is appendable,
    line-oriented and easy to inspect without extra dependencies.
    """

    return "\n".join(json.dumps(record.to_dict(), sort_keys=True) for record in records) + "\n"


def _is_station_header(stripped: str, lines: list[str], index: int) -> bool:
    if not stripped:
        return False
    if index + 1 >= len(lines):
        return False
    if not lines[index + 1].strip().startswith("==="):
        return False
    return bool(re.fullmatch(r"[A-Z0-9_ ]+", stripped))


def _record_from_match(station: str, row: re.Match[str]) -> HourlyForecast:
    month = _MONTHS[row.group("month")]
    forecast_at = datetime(
        year=int(row.group("year")),
        month=month,
        day=int(row.group("day")),
        hour=int(row.group("hour")),
    )

    return HourlyForecast(
        station=station,
        forecast_at=forecast_at,
        temperature_c=float(row.group("temperature")),
        wind_direction_deg=int(row.group("wind_direction")),
        wind_speed_kmh=int(row.group("wind_speed")),
        precipitation_mm=float(row.group("precipitation")),
    )
