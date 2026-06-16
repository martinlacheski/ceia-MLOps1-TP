from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

DEFAULT_SERVING_DIR = Path("data/models/rain_t1/current")
DEFAULT_MODEL_FILENAME = "model.joblib"
DEFAULT_METADATA_FILENAME = "metadata.json"
DEFAULT_THRESHOLD = 0.30
DEFAULT_FORECAST_RAIN_THRESHOLD_MM = 0.1
DEFAULT_REFERENCE_STATION = "OBERA_AERO"
REFERENCE_STATION_PRIORITY = (
    "OBERA_AERO",
    "POSADAS_AERO",
    "IGUAZU_AERO",
    "BERNARDO_DE_IRIGOYEN_AERO",
)


@dataclass(frozen=True)
class ServingBundle:
    estimator: Any
    metadata: dict[str, Any]
    model_path: Path
    metadata_path: Path


def export_serving_bundle(
    *,
    estimator: Any,
    serving_output_dir: Path,
    metadata: dict[str, Any],
) -> dict[str, str]:
    """Exporta un artefacto local estable para serving sin depender de MLflow."""

    serving_output_dir.mkdir(parents=True, exist_ok=True)
    model_path = serving_output_dir / DEFAULT_MODEL_FILENAME
    metadata_path = serving_output_dir / DEFAULT_METADATA_FILENAME
    tmp_model_path = serving_output_dir / f"{DEFAULT_MODEL_FILENAME}.tmp"
    tmp_metadata_path = serving_output_dir / f"{DEFAULT_METADATA_FILENAME}.tmp"

    joblib.dump(estimator, tmp_model_path)
    tmp_model_path.replace(model_path)

    tmp_metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_metadata_path.replace(metadata_path)

    return {
        "directory": str(serving_output_dir),
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
    }


def load_serving_bundle(serving_dir: Path) -> ServingBundle:
    model_path = serving_dir / DEFAULT_MODEL_FILENAME
    metadata_path = serving_dir / DEFAULT_METADATA_FILENAME
    if not model_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(f"Serving bundle incompleto en {serving_dir}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    estimator = joblib.load(model_path)
    return ServingBundle(
        estimator=estimator,
        metadata=metadata,
        model_path=model_path,
        metadata_path=metadata_path,
    )


def load_latest_feature_row(dataset_path: Path, feature_columns: list[str]) -> tuple[pd.Series, date]:
    dataset = pd.read_parquet(dataset_path)
    if "fecha" not in dataset.columns:
        raise ValueError("El dataset supervisado debe incluir la columna 'fecha'")

    missing_columns = [column for column in feature_columns if column not in dataset.columns]
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas para inferencia: {missing_columns}")

    work = dataset.copy()
    work["fecha"] = pd.to_datetime(work["fecha"])
    latest_row = work.sort_values("fecha", kind="stable").iloc[-1]
    latest_feature_date = latest_row["fecha"].date()
    return latest_row, latest_feature_date


def build_local_prediction(
    *,
    target_date: date,
    serving_dir: Path,
    dataset_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = load_serving_bundle(serving_dir)
    feature_columns = bundle.metadata["feature_columns"]
    latest_row, latest_feature_date = load_latest_feature_row(dataset_path, feature_columns)

    feature_frame = pd.DataFrame([{column: latest_row[column] for column in feature_columns}], columns=feature_columns)
    probability = float(bundle.estimator.predict_proba(feature_frame)[0][1])
    threshold = float(bundle.metadata.get("threshold", DEFAULT_THRESHOLD))
    modeled_target_date = latest_feature_date + timedelta(days=1)

    if target_date == modeled_target_date:
        target_alignment = "exact_t_plus_1"
    elif target_date > modeled_target_date:
        target_alignment = "beyond_available_local_features"
    else:
        target_alignment = "before_latest_modeled_target"

    return (
        {
            "source": "local_model_artifact",
            "model_name": bundle.metadata.get("registered_model_name")
            or bundle.metadata.get("model_name", "unknown_model"),
            "model_stage": bundle.metadata.get("model_stage", "current"),
            "rain_probability": round(probability, 4),
            "threshold": threshold,
            "will_rain": probability >= threshold,
        },
        {
            "feature_date": latest_feature_date.isoformat(),
            "modeled_target_date": modeled_target_date.isoformat(),
            "target_alignment": target_alignment,
            "serving_source": "local_artifact",
        },
    )


def build_prediction_fallback(reason: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        {
            "source": "local_model_unavailable",
            "model_name": "artifact_missing",
            "model_stage": "unavailable",
            "rain_probability": 0.0,
            "threshold": DEFAULT_THRESHOLD,
            "will_rain": False,
        },
        {
            "feature_date": None,
            "modeled_target_date": None,
            "target_alignment": "unavailable",
            "serving_source": reason,
        },
    )


def _load_smn_records(smn_path: Path) -> list[dict[str, Any]]:
    if not smn_path.exists():
        return []

    records: list[dict[str, Any]] = []
    for raw_line in smn_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        payload["forecast_date"] = date.fromisoformat(payload["forecast_date"])
        payload["station"] = str(payload["station"])
        payload["precipitation_mm"] = float(payload.get("precipitation_mm", 0.0))
        payload["forecast_steps"] = int(payload.get("forecast_steps", 0))
        records.append(payload)
    return records


def _station_priority(station: str, reference_station: str) -> tuple[int, int, str]:
    if station == reference_station:
        return (0, 0, station)
    if station in REFERENCE_STATION_PRIORITY:
        return (1, REFERENCE_STATION_PRIORITY.index(station), station)
    return (2, 999, station)


def build_smn_forecast(
    *,
    target_date: date,
    smn_path: Path,
    reference_station: str = DEFAULT_REFERENCE_STATION,
) -> tuple[dict[str, Any], dict[str, Any]]:
    records = _load_smn_records(smn_path)
    if not records:
        return (
            {
                "source": "SMN pron5d fallback",
                "reference_station": reference_station,
                "precipitation_mm": 0.0,
                "will_rain": False,
            },
            {
                "status": "file_missing_or_empty",
                "selected_station_reason": "No se encontró pronóstico SMN procesado; se usa fallback demostrable.",
                "forecast_date": None,
                "forecast_steps": None,
            },
        )

    same_date = [record for record in records if record["forecast_date"] == target_date]
    if same_date:
        selected = min(same_date, key=lambda record: _station_priority(record["station"], reference_station))
        status = "exact_date_reference_station" if selected["station"] == reference_station else "exact_date_station_fallback"
        reason = (
            f"Se usó la estación de referencia {reference_station}."
            if selected["station"] == reference_station
            else f"No hubo estación de referencia {reference_station}; se eligió {selected['station']} por prioridad de Misiones."
        )
    else:
        selected = min(
            records,
            key=lambda record: (
                abs((record["forecast_date"] - target_date).days),
                0 if record["forecast_date"] >= target_date else 1,
                *_station_priority(record["station"], reference_station),
            ),
        )
        status = "closest_date_fallback"
        reason = (
            f"No hubo coincidencia exacta para {target_date.isoformat()}; se usó {selected['forecast_date'].isoformat()} "
            f"en {selected['station']} como señal más cercana disponible."
        )

    precipitation_mm = float(selected["precipitation_mm"])
    return (
        {
            "source": "SMN pron5d",
            "reference_station": selected["station"],
            "precipitation_mm": round(precipitation_mm, 3),
            "will_rain": precipitation_mm >= DEFAULT_FORECAST_RAIN_THRESHOLD_MM,
        },
        {
            "status": status,
            "selected_station_reason": reason,
            "forecast_date": selected["forecast_date"].isoformat(),
            "forecast_steps": selected.get("forecast_steps"),
        },
    )


def build_operational_decision(prediction: dict[str, Any], forecast: dict[str, Any]) -> dict[str, str]:
    if prediction["will_rain"] and forecast["will_rain"]:
        return {
            "recommended_guard": "reforzada",
            "risk_level": "alto",
            "reason": "El modelo local supera el umbral operativo y el SMN también anticipa precipitación.",
        }
    if prediction["will_rain"] or forecast["will_rain"]:
        return {
            "recommended_guard": "preventiva",
            "risk_level": "medio",
            "reason": "Solo una de las señales anticipa lluvia; conviene seguimiento preventivo.",
        }
    return {
        "recommended_guard": "normal",
        "risk_level": "bajo",
        "reason": "Ni el modelo local ni el SMN muestran señal suficiente de lluvia.",
    }


def build_recommendation_payload(
    *,
    target_date: date,
    serving_dir: Path,
    dataset_path: Path,
    smn_path: Path,
    training_summary_path: Path,
    reference_station: str = DEFAULT_REFERENCE_STATION,
) -> dict[str, Any]:
    degradation_reasons: list[str] = []

    try:
        prediction, prediction_context = build_local_prediction(
            target_date=target_date,
            serving_dir=serving_dir,
            dataset_path=dataset_path,
        )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        prediction, prediction_context = build_prediction_fallback(str(exc))
        degradation_reasons.append(f"Local model fallback: {exc}")

    if prediction_context["target_alignment"] != "exact_t_plus_1":
        degradation_reasons.append(f"Prediction alignment: {prediction_context['target_alignment']}")

    forecast, forecast_context = build_smn_forecast(
        target_date=target_date,
        smn_path=smn_path,
        reference_station=reference_station,
    )
    if forecast_context["status"] != "exact_date_reference_station":
        degradation_reasons.append(f"SMN status: {forecast_context['status']}")

    if (
        prediction["source"] == "local_model_artifact"
        and forecast["source"] == "SMN pron5d"
        and not degradation_reasons
    ):
        mode = "model_artifact_and_smn"
    elif prediction["source"] == "local_model_artifact" and forecast["source"] == "SMN pron5d":
        mode = "degraded_fallback"
    elif prediction["source"] == "local_model_artifact":
        mode = "model_artifact_only_fallback"
    elif forecast["source"] == "SMN pron5d":
        mode = "smn_only_fallback"
    else:
        mode = "degraded_fallback"

    decision = build_operational_decision(prediction, forecast)
    return {
        "target_date": target_date,
        "prediction": prediction,
        "forecast": forecast,
        "decision": decision,
        "metadata": {
            "generated_at": datetime.now(timezone.utc),
            "mode": mode,
            "training_summary_path": str(training_summary_path),
            "serving_artifact_path": str(serving_dir),
            "smn_data_path": str(smn_path),
            "degradation_reasons": degradation_reasons,
            "prediction_context": prediction_context,
            "forecast_context": forecast_context,
        },
    }
