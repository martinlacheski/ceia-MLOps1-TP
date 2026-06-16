from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


DEFAULT_INPUT = Path("data/processed/rain_training_base.parquet")
DEFAULT_OUTPUT = Path("data/reports/rain_t1_training_summary.json")
DEFAULT_SERVING_OUTPUT_DIR = Path("data/models/rain_t1/current")
DEFAULT_EXPERIMENT_NAME = "rain-t1-training"
DEFAULT_REGISTERED_MODEL_NAME = "ceml-rain-rain-t1-classifier"
DEFAULT_TEST_FRACTION = 0.2
DEFAULT_RANDOM_STATE = 42
DEFAULT_OPERATIONAL_THRESHOLD = 0.30
FEATURE_PREFIXES = (
    "lluvia_mm_lag_",
    "llovio_lag_",
    "lluvia_mm_rolling_",
    "dias_lluvia_rolling_",
)
CALENDAR_FEATURES = ("mes", "dia_anio", "dia_semana")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    model_type: str
    params: dict[str, Any]
    estimator: Any


def select_training_features(columns: list[str]) -> list[str]:
    """Selecciona solo features past-only y de calendario para evitar leakage."""

    selected = [
        column
        for column in columns
        if any(column.startswith(prefix) for prefix in FEATURE_PREFIXES) or column in CALENDAR_FEATURES
    ]
    return sorted(selected)


def temporal_train_test_split(dataset: "pd.DataFrame", test_fraction: float) -> tuple["pd.DataFrame", "pd.DataFrame"]:
    """Separa train/test respetando el orden temporal del dataset."""

    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction debe estar entre 0 y 1")

    work = dataset.sort_values("fecha", kind="stable").reset_index(drop=True)
    split_index = int(len(work) * (1 - test_fraction))
    split_index = max(1, min(split_index, len(work) - 1))
    return work.iloc[:split_index].copy(), work.iloc[split_index:].copy()


def build_candidate_specs(
    *,
    random_state: int,
    include_xgboost: bool,
    scale_pos_weight: float | None = None,
) -> tuple[list[CandidateSpec], list[dict[str, str]]]:
    """Construye los modelos candidatos disponibles para clasificación binaria."""

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    candidates = [
        CandidateSpec(
            name="logistic_regression",
            model_type="sklearn",
            params={
                "class_weight": "balanced",
                "max_iter": 1000,
                "solver": "lbfgs",
                "random_state": random_state,
            },
            estimator=Pipeline(
                steps=[
                    ("scaler", StandardScaler()),
                    (
                        "classifier",
                        LogisticRegression(
                            class_weight="balanced",
                            max_iter=1000,
                            solver="lbfgs",
                            random_state=random_state,
                        ),
                    ),
                ]
            ),
        ),
        CandidateSpec(
            name="random_forest",
            model_type="sklearn",
            params={
                "n_estimators": 300,
                "max_depth": 8,
                "min_samples_leaf": 2,
                "class_weight": "balanced_subsample",
                "random_state": random_state,
            },
            estimator=RandomForestClassifier(
                n_estimators=300,
                max_depth=8,
                min_samples_leaf=2,
                class_weight="balanced_subsample",
                random_state=random_state,
                n_jobs=-1,
            ),
        ),
    ]
    skipped: list[dict[str, str]] = []

    if not include_xgboost:
        skipped.append({"model": "xgboost_classifier", "reason": "disabled_by_flag"})
        return candidates, skipped

    try:
        from xgboost import XGBClassifier
    except ModuleNotFoundError:
        skipped.append({"model": "xgboost_classifier", "reason": "xgboost_not_installed"})
        return candidates, skipped

    candidates.append(
        CandidateSpec(
            name="xgboost_classifier",
            model_type="xgboost",
            params={
                "n_estimators": 300,
                "max_depth": 4,
                "learning_rate": 0.05,
                "subsample": 0.9,
                "colsample_bytree": 0.9,
                "eval_metric": "logloss",
                "random_state": random_state,
                "scale_pos_weight": scale_pos_weight,
            },
            estimator=XGBClassifier(
                n_estimators=300,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
                random_state=random_state,
                scale_pos_weight=scale_pos_weight,
                n_jobs=1,
            ),
        )
    )
    return candidates, skipped


def evaluate_candidate(spec: CandidateSpec, x_train: Any, y_train: Any, x_test: Any, y_test: Any) -> dict[str, Any]:
    """Entrena un candidato y devuelve métricas y artefactos intermedios."""

    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    estimator = spec.estimator
    estimator.fit(x_train, y_train)
    y_pred = estimator.predict(x_test)

    probabilities: Any | None = None
    if hasattr(estimator, "predict_proba"):
        probabilities = estimator.predict_proba(x_test)[:, 1]
    elif hasattr(estimator, "decision_function"):
        probabilities = estimator.decision_function(x_test)

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "positive_rate_predicted": round(float(y_pred.mean()), 4),
        "positive_rate_real": round(float(y_test.mean()), 4),
    }
    if probabilities is not None and len(set(y_test.tolist())) > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(y_test, probabilities)), 4)
        metrics["average_precision"] = round(float(average_precision_score(y_test, probabilities)), 4)

    primary_metric = metrics.get("average_precision", metrics["f1"])
    return {
        "model_name": spec.name,
        "model_type": spec.model_type,
        "params": spec.params,
        "metrics": metrics,
        "primary_metric": round(float(primary_metric), 4),
        "estimator": estimator,
    }


def load_baseline_reference(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    best_name = payload.get("best_by_f1")
    best_baseline = next(
        (item for item in payload.get("baselines", []) if item.get("baseline_name") == best_name),
        None,
    )
    return {
        "source": str(path),
        "best_by_f1": best_name,
        "best_f1": best_baseline.get("metrics", {}).get("f1") if best_baseline else None,
    }


def run_training(
    input_path: Path,
    output_path: Path,
    *,
    serving_output_dir: Path = DEFAULT_SERVING_OUTPUT_DIR,
    test_fraction: float = DEFAULT_TEST_FRACTION,
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    tracking_uri: str | None = None,
    registered_model_name: str | None = DEFAULT_REGISTERED_MODEL_NAME,
    include_xgboost: bool = True,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> dict[str, Any]:
    """Entrena candidatos supervisados de lluvia t+1 y registra el mejor en MLflow."""

    import mlflow
    import mlflow.sklearn
    import pandas as pd
    from ceml_rain.inference.serving import export_serving_bundle
    from mlflow.models import infer_signature

    dataset = pd.read_parquet(input_path)
    if "fecha" not in dataset.columns or "y_llueve_t1" not in dataset.columns:
        raise ValueError("El dataset de entrenamiento debe incluir 'fecha' e 'y_llueve_t1'")

    dataset = dataset.copy()
    dataset["fecha"] = pd.to_datetime(dataset["fecha"])
    dataset = dataset.sort_values("fecha", kind="stable").reset_index(drop=True)

    feature_columns = select_training_features(dataset.columns.tolist())
    if not feature_columns:
        raise ValueError("No se encontraron features past-only válidas para entrenar")

    train_df, test_df = temporal_train_test_split(dataset, test_fraction=test_fraction)
    x_train = train_df[feature_columns]
    y_train = train_df["y_llueve_t1"].astype(int)
    x_test = test_df[feature_columns]
    y_test = test_df["y_llueve_t1"].astype(int)

    positive_count = int(y_train.sum())
    negative_count = int(len(y_train) - positive_count)
    scale_pos_weight = round(negative_count / positive_count, 4) if positive_count else None

    candidates, skipped_candidates = build_candidate_specs(
        random_state=random_state,
        include_xgboost=include_xgboost,
        scale_pos_weight=scale_pos_weight,
    )
    if not candidates:
        raise ValueError("No hay modelos candidatos disponibles para entrenar")

    results = [evaluate_candidate(spec, x_train, y_train, x_test, y_test) for spec in candidates]
    best_result = max(
        results,
        key=lambda item: (
            item["primary_metric"],
            item["metrics"].get("f1", 0.0),
            item["metrics"].get("roc_auc", 0.0),
        ),
    )
    baseline_reference = load_baseline_reference(input_path.parent.parent / "reports" / "rain_baseline_metrics.json")

    resolved_tracking_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI") or "file:./mlruns"
    mlflow.set_tracking_uri(resolved_tracking_uri)
    mlflow.set_experiment(experiment_name)

    registration: dict[str, Any] = {
        "requested_model_name": registered_model_name,
        "status": "not_requested" if not registered_model_name else "pending",
    }

    with mlflow.start_run(run_name="rain_t1_supervised_training") as run:
        mlflow.log_param("input_path", str(input_path))
        mlflow.log_param("test_fraction", test_fraction)
        mlflow.log_param("feature_count", len(feature_columns))
        mlflow.log_param("selected_models", ",".join(result["model_name"] for result in results))
        mlflow.log_param("best_model_name", best_result["model_name"])
        mlflow.log_param("primary_metric", "average_precision_then_f1")
        mlflow.log_param("random_state", random_state)
        mlflow.set_tag("problem_type", "binary_classification")
        mlflow.set_tag("target", "y_llueve_t1")
        mlflow.set_tag("selection_policy", "Prefer average precision when available; otherwise use F1.")

        split_summary = {
            "train_rows": int(len(train_df)),
            "test_rows": int(len(test_df)),
            "train_positive_rate": round(float(y_train.mean()), 4),
            "test_positive_rate": round(float(y_test.mean()), 4),
            "train_date_min": train_df["fecha"].min().date().isoformat(),
            "train_date_max": train_df["fecha"].max().date().isoformat(),
            "test_date_min": test_df["fecha"].min().date().isoformat(),
            "test_date_max": test_df["fecha"].max().date().isoformat(),
        }
        mlflow.log_metrics(
            {
                "train_positive_rate": split_summary["train_positive_rate"],
                "test_positive_rate": split_summary["test_positive_rate"],
                "best_primary_metric": best_result["primary_metric"],
            }
        )

        for result in results:
            for key, value in result["params"].items():
                mlflow.log_param(f"{result['model_name']}.{key}", value)
            for key, value in result["metrics"].items():
                mlflow.log_metric(f"{result['model_name']}.{key}", value)

        signature = infer_signature(x_train, best_result["estimator"].predict(x_train))
        input_example = x_test.head(5)
        model_info = mlflow.sklearn.log_model(
            sk_model=best_result["estimator"],
            name="model",
            signature=signature,
            input_example=input_example,
        )

        if registered_model_name:
            try:
                model_version = mlflow.register_model(
                    model_uri=model_info.model_uri,
                    name=registered_model_name,
                )
                registration = {
                    "requested_model_name": registered_model_name,
                    "status": "registered",
                    "version": getattr(model_version, "version", None),
                }
            except Exception as exc:  # pragma: no cover
                registration = {
                    "requested_model_name": registered_model_name,
                    "status": "registration_failed",
                    "reason": str(exc),
                }

        generated_at = datetime.now(timezone.utc).isoformat()
        serving_metadata = {
            "generated_at": generated_at,
            "model_name": best_result["model_name"],
            "registered_model_name": registered_model_name,
            "model_type": best_result["model_type"],
            "feature_columns": feature_columns,
            "threshold": DEFAULT_OPERATIONAL_THRESHOLD,
            "metrics": best_result["metrics"],
            "training_summary_path": str(output_path),
            "model_stage": "current",
            "mlflow_run_id": run.info.run_id,
            "registered_model": registration,
        }
        serving_artifact = export_serving_bundle(
            estimator=best_result["estimator"],
            serving_output_dir=serving_output_dir,
            metadata=serving_metadata,
        )

        summary = {
            "training_type": "rain_t1_supervised_classification",
            "generated_at": generated_at,
            "input_path": str(input_path),
            "output_path": str(output_path),
            "serving_output_dir": str(serving_output_dir),
            "tracking_uri": resolved_tracking_uri,
            "experiment_name": experiment_name,
            "mlflow_run_id": run.info.run_id,
            "registered_model": registration,
            "selection_policy": "Prefer average precision when available; otherwise use F1 for imbalanced rain_t+1 classification.",
            "amq_reference": {
                "note": "AMQ operational regression favored XGBoost, but this workflow re-evaluates candidates for the different binary rain_t+1 target.",
                "xgboost_candidate_requested": include_xgboost,
            },
            "split": split_summary,
            "feature_columns": feature_columns,
            "skipped_candidates": skipped_candidates,
            "candidate_results": [
                {
                    "model_name": result["model_name"],
                    "model_type": result["model_type"],
                    "params": result["params"],
                    "metrics": result["metrics"],
                    "primary_metric": result["primary_metric"],
                }
                for result in results
            ],
            "best_model": {
                "model_name": best_result["model_name"],
                "model_type": best_result["model_type"],
                "params": best_result["params"],
                "metrics": best_result["metrics"],
                "primary_metric": best_result["primary_metric"],
            },
            "baseline_reference": baseline_reference,
            "serving_artifact": {
                **serving_artifact,
                "threshold": DEFAULT_OPERATIONAL_THRESHOLD,
                "generated_at": generated_at,
            },
        }

        mlflow.log_dict({"feature_columns": feature_columns}, "feature_columns.json")
        mlflow.log_dict(summary, "training_summary.json")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entrena modelos supervisados para lluvia t+1 y registra resultados en MLflow.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Dataset supervisado de lluvia.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Archivo JSON resumen para revisión local.")
    parser.add_argument(
        "--serving-output-dir",
        type=Path,
        default=DEFAULT_SERVING_OUTPUT_DIR,
        help="Directorio estable para exportar el artefacto local de serving.",
    )
    parser.add_argument(
        "--test-fraction",
        type=float,
        default=DEFAULT_TEST_FRACTION,
        help="Fracción temporal reservada para test holdout (ej. 0.2 = 20%% final).",
    )
    parser.add_argument("--experiment-name", default=DEFAULT_EXPERIMENT_NAME, help="Nombre del experimento en MLflow.")
    parser.add_argument(
        "--tracking-uri",
        default=None,
        help="Tracking URI de MLflow. Si se omite, usa MLFLOW_TRACKING_URI o file:./mlruns.",
    )
    parser.add_argument(
        "--registered-model-name",
        default=DEFAULT_REGISTERED_MODEL_NAME,
        help="Nombre a registrar en el Model Registry. Usar 'none' para desactivar registro.",
    )
    parser.add_argument(
        "--disable-xgboost",
        action="store_true",
        help="Desactiva explícitamente el candidato XGBoost aunque la dependencia exista.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada para entrenar el primer workflow supervisado de lluvia."""

    args = parse_args(argv)
    registered_model_name = None if str(args.registered_model_name).lower() == "none" else args.registered_model_name
    summary = run_training(
        input_path=args.input,
        output_path=args.output,
        serving_output_dir=args.serving_output_dir,
        test_fraction=args.test_fraction,
        experiment_name=args.experiment_name,
        tracking_uri=args.tracking_uri,
        registered_model_name=registered_model_name,
        include_xgboost=not args.disable_xgboost,
    )
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
