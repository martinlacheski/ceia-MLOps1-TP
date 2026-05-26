from datetime import date, datetime

from ceml_rain.smn.pron5d import (
    aggregate_daily_precipitation,
    build_daily_misiones_forecast,
    daily_precipitation_to_jsonl,
    parse_misiones_pron5d_text,
    parse_pron5d_text,
)


SAMPLE_PRON5D = """
 ************************************************************************************************
 Producto basado en un modelo de pronóstico numérico del tiempo,
 por lo tanto puede diferir del pronostico emitido por el SMN
 ************************************************************************************************

 AEROPARQUE
 ================================================================================================
      FECHA *          TEMPERATURA      VIENTO      PRECIPITACION(mm)
                                     (DIR | KM/H)
 ================================================================================================
  26/MAY/2026 00Hs.         9.8       205 |   4         0.0
  26/MAY/2026 03Hs.         9.5       191 |   5         0.1

 OBERA_AERO
 ================================================================================================
      FECHA *          TEMPERATURA      VIENTO      PRECIPITACION(mm)
                                     (DIR | KM/H)
 ================================================================================================
  26/MAY/2026 00Hs.        17.2        90 |   4         1.0
  26/MAY/2026 03Hs.        16.8       110 |   5         2.5
  27/MAY/2026 00Hs.        15.1       120 |   8         0.0

 POSADAS_AERO
 ================================================================================================
      FECHA *          TEMPERATURA      VIENTO      PRECIPITACION(mm)
                                     (DIR | KM/H)
 ================================================================================================
  26/MAY/2026 00Hs.        19.5        80 |   6         0.2
"""


def test_parse_pron5d_text_reads_hourly_rows_for_allowed_station():
    records = parse_pron5d_text(SAMPLE_PRON5D, stations=["OBERA_AERO"])

    assert len(records) == 3
    assert records[0].station == "OBERA_AERO"
    assert records[0].forecast_at == datetime(2026, 5, 26, 0)
    assert records[0].temperature_c == 17.2
    assert records[0].wind_direction_deg == 90
    assert records[0].wind_speed_kmh == 4
    assert records[0].precipitation_mm == 1.0


def test_parse_misiones_pron5d_text_filters_project_stations():
    records = parse_misiones_pron5d_text(SAMPLE_PRON5D)

    assert {record.station for record in records} == {"OBERA_AERO", "POSADAS_AERO"}


def test_aggregate_daily_precipitation_groups_by_station_and_date():
    records = parse_misiones_pron5d_text(SAMPLE_PRON5D)

    daily = aggregate_daily_precipitation(records)

    assert daily[0].station == "OBERA_AERO"
    assert daily[0].forecast_date == date(2026, 5, 26)
    assert daily[0].precipitation_mm == 3.5
    assert daily[0].forecast_steps == 2
    assert daily[1].station == "OBERA_AERO"
    assert daily[1].forecast_date == date(2026, 5, 27)
    assert daily[2].station == "POSADAS_AERO"
    assert daily[2].precipitation_mm == 0.2


def test_build_daily_misiones_forecast_uses_provided_text_without_network():
    daily = build_daily_misiones_forecast(SAMPLE_PRON5D)

    assert len(daily) == 3
    assert daily[0].station == "OBERA_AERO"
    assert daily[0].forecast_date == date(2026, 5, 26)


def test_daily_precipitation_to_jsonl_serializes_records():
    daily = build_daily_misiones_forecast(SAMPLE_PRON5D)

    payload = daily_precipitation_to_jsonl(daily)

    assert '"station": "OBERA_AERO"' in payload
    assert '"forecast_date": "2026-05-26"' in payload
    assert '"forecast_steps": 2' in payload
    assert payload.endswith("\n")
