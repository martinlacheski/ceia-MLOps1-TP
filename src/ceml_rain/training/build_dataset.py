from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


DEFAULT_INPUT = Path("data/processed/lluvia_diaria_clean.parquet")
DEFAULT_OUTPUT = Path("data/processed/rain_training_base.parquet")
DEFAULT_SUMMARY = Path("data/reports/rain_training_base_summary.json")

LAG_DAYS = (1, 2, 3, 7, 14, 30)
ROLLING_WINDOWS = (7, 14, 30)


def build_rain_training_dataset(input_path: Path) -> pd.DataFrame:
    """Construye el dataset supervisado de lluvia `t+1` desde el histórico diario."""

    rainfall = pd.read_parquet(input_path)
    required_columns = {"fecha", "lluvia_mm", "lluvia_status"}
    missing_columns = required_columns.difference(rainfall.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Faltan columnas requeridas en el dataset de lluvia: {missing}")

    dataset = rainfall.copy()
    dataset["fecha"] = pd.to_datetime(dataset["fecha"])
    dataset = dataset.sort_values("fecha", kind="stable").reset_index(drop=True)
    dataset["lluvia_mm"] = pd.to_numeric(dataset["lluvia_mm"], errors="coerce")
    dataset["llovio"] = dataset["lluvia_mm"] > 0

    for days in LAG_DAYS:
        dataset[f"lluvia_mm_lag_{days}"] = dataset["lluvia_mm"].shift(days)
        dataset[f"llovio_lag_{days}"] = dataset["llovio"].shift(days)

    past_rain = dataset["lluvia_mm"].shift(1)
    for window in ROLLING_WINDOWS:
        dataset[f"lluvia_mm_rolling_{window}_sum"] = past_rain.rolling(window=window).sum()
        dataset[f"lluvia_mm_rolling_{window}_mean"] = past_rain.rolling(window=window).mean()
        dataset[f"dias_lluvia_rolling_{window}"] = dataset["llovio"].shift(1).rolling(window=window).sum()

    dataset["mes"] = dataset["fecha"].dt.month
    dataset["dia_anio"] = dataset["fecha"].dt.dayofyear
    dataset["dia_semana"] = dataset["fecha"].dt.dayofweek
    dataset["y_lluvia_mm_t1"] = dataset["lluvia_mm"].shift(-1)
    dataset["y_llueve_t1"] = dataset["y_lluvia_mm_t1"] > 0

    feature_columns = [
        column
        for column in dataset.columns
        if column.startswith("lluvia_mm_lag_")
        or column.startswith("llovio_lag_")
        or column.startswith("lluvia_mm_rolling_")
        or column.startswith("dias_lluvia_rolling_")
    ]
    required_for_training = feature_columns + ["y_lluvia_mm_t1", "y_llueve_t1"]
    dataset = dataset.dropna(subset=required_for_training).reset_index(drop=True)

    return dataset


def summarize_dataset(dataset: pd.DataFrame, input_path: Path, output_path: Path) -> dict[str, object]:
    """Genera un resumen simple para auditar el dataset creado."""

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "rows": int(len(dataset)),
        "columns": list(dataset.columns),
        "date_min": dataset["fecha"].min().date().isoformat(),
        "date_max": dataset["fecha"].max().date().isoformat(),
        "rainy_target_rows": int(dataset["y_llueve_t1"].sum()),
        "dry_target_rows": int((~dataset["y_llueve_t1"]).sum()),
        "rainy_target_rate": round(float(dataset["y_llueve_t1"].mean()), 4),
    }


def write_dataset(dataset: pd.DataFrame, output_path: Path) -> None:
    """Persiste el dataset según la extensión del archivo de salida."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        dataset.to_parquet(output_path, index=False)
        return
    if output_path.suffix == ".jsonl":
        dataset.to_json(output_path, orient="records", lines=True, date_format="iso")
        return
    if output_path.suffix == ".csv":
        dataset.to_csv(output_path, index=False)
        return
    raise ValueError("La salida debe tener extensión .parquet, .jsonl o .csv")


def run_build_dataset(input_path: Path, output_path: Path, summary_path: Path | None = DEFAULT_SUMMARY) -> dict[str, object]:
    """Construye, persiste y resume el dataset de entrenamiento."""

    dataset = build_rain_training_dataset(input_path)
    write_dataset(dataset, output_path)
    summary = summarize_dataset(dataset, input_path=input_path, output_path=output_path)

    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return summary


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada para generar el dataset desde consola."""

    parser = argparse.ArgumentParser(description="Construye el dataset supervisado de lluvia `t+1` para ML-RainOps.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Parquet histórico de lluvia diaria.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Archivo de salida .parquet, .jsonl o .csv.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=DEFAULT_SUMMARY,
        help="Archivo JSON de resumen. Usar 'none' para no escribir resumen.",
    )
    args = parser.parse_args(argv)

    summary_path = None if str(args.summary).lower() == "none" else args.summary
    summary = run_build_dataset(input_path=args.input, output_path=args.output, summary_path=summary_path)
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
