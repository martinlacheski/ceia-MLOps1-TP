from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
from typing import Any

try:
    from airflow.decorators import dag, task
    from airflow.exceptions import AirflowException
except ModuleNotFoundError:  # pragma: no cover - fallback para tests locales sin Airflow instalado.
    dag = None
    task = None

    class AirflowException(RuntimeError):
        """Fallback mínimo para tests locales."""


PROJECT_ROOT = Path("/opt/ml-rainops")
SRC_DIR = PROJECT_ROOT / "src"
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "rain_training_base.parquet"
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "rain_t1_training_summary.json"
SERVING_OUTPUT_DIR = PROJECT_ROOT / "data" / "models" / "rain_t1" / "current"
TMP_REPORT_PATH = Path("/tmp/rain_t1_training_summary.json")
DEFAULT_TRACKING_URI = "http://mlflow:5000"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def resolve_tracking_uri() -> str:
    return os.getenv("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI)


def build_compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    best_model = summary.get("best_model", {})
    metrics = best_model.get("metrics", {})
    registration = summary.get("registered_model", {})

    return {
        "model_name": best_model.get("model_name"),
        "run_id": summary.get("mlflow_run_id"),
        "version": registration.get("version"),
        "average_precision": metrics.get("average_precision"),
        "f1": metrics.get("f1"),
        "serving_output_dir": summary.get("serving_output_dir"),
    }


def copy_summary_file(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Training summary not found at {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


if dag is not None and task is not None:

    @dag(
        dag_id="rain_t1_training",
        description="Entrena el clasificador supervisado de lluvia t+1 y deja evidencia en MLflow.",
        schedule=None,
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["training", "rainops", "mlflow"],
    )
    def rain_t1_training():
        @task
        def train_model() -> dict[str, Any]:
            from ceml_rain.training.train import run_training

            tracking_uri = resolve_tracking_uri()
            os.environ["MLFLOW_TRACKING_URI"] = tracking_uri

            summary = run_training(
                input_path=INPUT_PATH,
                output_path=TMP_REPORT_PATH,
                serving_output_dir=SERVING_OUTPUT_DIR,
                tracking_uri=tracking_uri,
            )

            compact = build_compact_summary(summary)
            compact["summary_path"] = str(TMP_REPORT_PATH)
            return compact

        @task
        def persist_summary(training_result: dict[str, Any]) -> dict[str, Any]:
            try:
                copy_summary_file(TMP_REPORT_PATH, REPORT_PATH)
            except PermissionError as exc:
                raise AirflowException(
                    "No se pudo copiar el resumen de entrenamiento a "
                    f"{REPORT_PATH}. Verificá que airflow-init haya preparado permisos de data/reports/."
                ) from exc
            except OSError as exc:
                raise AirflowException(
                    "Falló la persistencia del resumen de entrenamiento en data/reports: "
                    f"{exc}"
                ) from exc

            return {
                "model_name": training_result.get("model_name"),
                "run_id": training_result.get("run_id"),
                "version": training_result.get("version"),
                "average_precision": training_result.get("average_precision"),
                "f1": training_result.get("f1"),
                "summary_path": str(REPORT_PATH),
                "serving_output_dir": str(SERVING_OUTPUT_DIR),
            }

        persist_summary(train_model())


    rain_t1_training()
