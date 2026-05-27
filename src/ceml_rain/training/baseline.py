from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


DEFAULT_INPUT = Path("data/processed/rain_training_base.parquet")
DEFAULT_OUTPUT = Path("data/reports/rain_baseline_metrics.json")


def evaluate_rain_baselines(
    dataset: pd.DataFrame,
    *,
    rolling_7_threshold_mm: float = 10.0,
    monthly_rate_threshold: float = 0.35,
) -> dict[str, object]:
    """Evalúa varios baselines simples para lluvia `t+1`.

    Las reglas usan solo señales disponibles hasta el día de predicción. La tasa
    mensual se calcula de forma expansiva y desplazada para no mirar el target
    de la fila actual.
    """

    required_columns = {
        "fecha",
        "mes",
        "dias_lluvia_rolling_7",
        "lluvia_mm_rolling_7_sum",
        "y_llueve_t1",
    }
    missing_columns = required_columns.difference(dataset.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Faltan columnas requeridas para los baselines: {missing}")

    work = dataset.copy()
    work["fecha"] = pd.to_datetime(work["fecha"])
    work = work.sort_values("fecha", kind="stable").reset_index(drop=True)
    y_true = work["y_llueve_t1"].astype(bool)
    historical_monthly_rate = _past_only_monthly_rate(work)

    baseline_predictions = {
        "recent_rain_any_7d": {
            "rule": "Predice lluvia mañana si hubo al menos un día con lluvia en los últimos 7 días.",
            "y_pred": work["dias_lluvia_rolling_7"] >= 1,
        },
        "recent_rain_mm_7d": {
            "rule": f"Predice lluvia mañana si la lluvia acumulada de los últimos 7 días es >= {rolling_7_threshold_mm:.1f} mm.",
            "y_pred": work["lluvia_mm_rolling_7_sum"] >= rolling_7_threshold_mm,
        },
        "monthly_rate_or_recent_mm_7d": {
            "rule": (
                f"Predice lluvia mañana si la tasa histórica past-only del mes es >= {monthly_rate_threshold:.2f} "
                f"o si la lluvia acumulada de los últimos 7 días es >= {rolling_7_threshold_mm:.1f} mm."
            ),
            "y_pred": (historical_monthly_rate >= monthly_rate_threshold)
            | (work["lluvia_mm_rolling_7_sum"] >= rolling_7_threshold_mm),
        },
    }

    baselines = [
        _evaluate_predictions(name=name, rule=payload["rule"], y_true=y_true, y_pred=payload["y_pred"])
        for name, payload in baseline_predictions.items()
    ]

    return {
        "evaluation_type": "rain_t1_baseline_comparison",
        "input_rows": int(len(work)),
        "date_min": work["fecha"].min().date().isoformat(),
        "date_max": work["fecha"].max().date().isoformat(),
        "positive_rate_real": round(float(y_true.mean()), 4),
        "parameters": {
            "rolling_7_threshold_mm": rolling_7_threshold_mm,
            "monthly_rate_threshold": monthly_rate_threshold,
        },
        "baselines": baselines,
        "best_by_f1": max(baselines, key=lambda item: item["metrics"]["f1"])["baseline_name"],
        "note": (
            "AMQ usó la lluvia como feature dentro de un baseline operativo más amplio. "
            "En ML-RainOps se compara un baseline específico para la dimensión lluvia t+1."
        ),
    }


def run_baseline(
    input_path: Path,
    output_path: Path,
    *,
    rolling_7_threshold_mm: float = 10.0,
    monthly_rate_threshold: float = 0.35,
) -> dict[str, object]:
    """Carga el dataset, evalúa baselines y escribe métricas en JSON."""

    dataset = pd.read_parquet(input_path)
    metrics = evaluate_rain_baselines(
        dataset,
        rolling_7_threshold_mm=rolling_7_threshold_mm,
        monthly_rate_threshold=monthly_rate_threshold,
    )
    metrics["input_path"] = str(input_path)
    metrics["output_path"] = str(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return metrics


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada para ejecutar los baselines desde consola."""

    parser = argparse.ArgumentParser(description="Evalúa baselines simples de lluvia `t+1`.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Dataset supervisado de lluvia.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Archivo JSON de métricas.")
    parser.add_argument(
        "--rolling-7-threshold-mm",
        type=float,
        default=10.0,
        help="Umbral de lluvia acumulada en 7 días para el baseline reciente.",
    )
    parser.add_argument(
        "--monthly-rate-threshold",
        type=float,
        default=0.35,
        help="Umbral de tasa histórica mensual past-only para el baseline estacional.",
    )
    args = parser.parse_args(argv)

    metrics = run_baseline(
        input_path=args.input,
        output_path=args.output,
        rolling_7_threshold_mm=args.rolling_7_threshold_mm,
        monthly_rate_threshold=args.monthly_rate_threshold,
    )
    sys.stdout.write(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")

    return 0


def _past_only_monthly_rate(dataset: pd.DataFrame) -> pd.Series:
    target_as_float = dataset["y_llueve_t1"].astype(float)
    monthly_rate = target_as_float.groupby(dataset["mes"], sort=False).transform(lambda values: values.shift(1).expanding().mean())
    global_rate = target_as_float.shift(1).expanding().mean()
    return monthly_rate.fillna(global_rate).fillna(0.0)


def _evaluate_predictions(name: str, rule: str, y_true: pd.Series, y_pred: pd.Series) -> dict[str, object]:
    y_pred = y_pred.astype(bool)
    true_positive = int((y_true & y_pred).sum())
    true_negative = int((~y_true & ~y_pred).sum())
    false_positive = int((~y_true & y_pred).sum())
    false_negative = int((y_true & ~y_pred).sum())
    total = int(len(y_true))

    accuracy = _safe_divide(true_positive + true_negative, total)
    precision = _safe_divide(true_positive, true_positive + false_positive)
    recall = _safe_divide(true_positive, true_positive + false_negative)
    f1 = _safe_divide(2 * precision * recall, precision + recall)

    return {
        "baseline_name": name,
        "rule": rule,
        "positive_rate_predicted": round(float(y_pred.mean()), 4),
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "confusion_matrix": {
            "true_positive": true_positive,
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
        },
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


if __name__ == "__main__":
    raise SystemExit(main())
