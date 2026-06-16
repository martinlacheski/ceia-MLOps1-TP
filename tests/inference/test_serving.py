from datetime import date
import json
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression

from ceml_rain.inference.serving import (
    build_local_prediction,
    build_recommendation_payload,
    build_smn_forecast,
    export_serving_bundle,
)


def _build_dataset(path: Path) -> None:
    dataset = pd.DataFrame(
        [
            {"fecha": "2026-03-28", "mes": 3, "dia_anio": 87, "dia_semana": 5, "lluvia_mm_lag_1": 0.0},
            {"fecha": "2026-03-29", "mes": 3, "dia_anio": 88, "dia_semana": 6, "lluvia_mm_lag_1": 8.1},
            {"fecha": "2026-03-30", "mes": 3, "dia_anio": 89, "dia_semana": 0, "lluvia_mm_lag_1": 3.4},
        ]
    )
    dataset.to_parquet(path, index=False)


def _build_estimator() -> LogisticRegression:
    features = pd.DataFrame(
        [
            {"mes": 3, "dia_anio": 87, "dia_semana": 5, "lluvia_mm_lag_1": 0.0},
            {"mes": 3, "dia_anio": 88, "dia_semana": 6, "lluvia_mm_lag_1": 8.0},
            {"mes": 3, "dia_anio": 89, "dia_semana": 0, "lluvia_mm_lag_1": 5.0},
            {"mes": 4, "dia_anio": 90, "dia_semana": 1, "lluvia_mm_lag_1": 0.1},
        ]
    )
    target = [0, 1, 1, 0]
    estimator = LogisticRegression(random_state=42)
    estimator.fit(features, target)
    return estimator


def test_build_local_prediction_uses_latest_feature_row_and_metadata(tmp_path):
    dataset_path = tmp_path / "rain_training_base.parquet"
    serving_dir = tmp_path / "current"
    _build_dataset(dataset_path)

    export_serving_bundle(
        estimator=_build_estimator(),
        serving_output_dir=serving_dir,
        metadata={
            "registered_model_name": "ceml-rain-rain-t1-classifier",
            "model_stage": "current",
            "feature_columns": ["mes", "dia_anio", "dia_semana", "lluvia_mm_lag_1"],
            "threshold": 0.3,
        },
    )

    prediction, context = build_local_prediction(
        target_date=date(2026, 3, 31),
        serving_dir=serving_dir,
        dataset_path=dataset_path,
    )

    assert prediction["source"] == "local_model_artifact"
    assert prediction["model_name"] == "ceml-rain-rain-t1-classifier"
    assert 0.0 <= prediction["rain_probability"] <= 1.0
    assert context == {
        "feature_date": "2026-03-30",
        "modeled_target_date": "2026-03-31",
        "target_alignment": "exact_t_plus_1",
        "serving_source": "local_artifact",
    }


def test_build_smn_forecast_prefers_reference_station_and_falls_back_to_closest_date(tmp_path):
    smn_path = tmp_path / "smn_pron5d_daily.jsonl"
    smn_path.write_text(
        "\n".join(
            [
                json.dumps({"forecast_date": "2026-05-29", "forecast_steps": 8, "precipitation_mm": 0.4, "station": "OBERA_AERO"}),
                json.dumps({"forecast_date": "2026-05-29", "forecast_steps": 8, "precipitation_mm": 2.9, "station": "IGUAZU_AERO"}),
                json.dumps({"forecast_date": "2026-05-31", "forecast_steps": 8, "precipitation_mm": 0.2, "station": "POSADAS_AERO"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    forecast_exact, context_exact = build_smn_forecast(target_date=date(2026, 5, 29), smn_path=smn_path)
    forecast_closest, context_closest = build_smn_forecast(target_date=date(2026, 5, 30), smn_path=smn_path)

    assert forecast_exact["reference_station"] == "OBERA_AERO"
    assert forecast_exact["will_rain"] is True
    assert context_exact["status"] == "exact_date_reference_station"
    assert forecast_closest["reference_station"] == "POSADAS_AERO"
    assert context_closest["status"] == "closest_date_fallback"


def test_build_recommendation_payload_uses_smn_only_fallback_when_artifact_is_missing(tmp_path):
    dataset_path = tmp_path / "rain_training_base.parquet"
    smn_path = tmp_path / "smn_pron5d_daily.jsonl"
    _build_dataset(dataset_path)
    smn_path.write_text(
        json.dumps(
            {"forecast_date": "2026-03-31", "forecast_steps": 8, "precipitation_mm": 1.2, "station": "OBERA_AERO"}
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_recommendation_payload(
        target_date=date(2026, 3, 31),
        serving_dir=tmp_path / "missing-artifact",
        dataset_path=dataset_path,
        smn_path=smn_path,
        training_summary_path=tmp_path / "summary.json",
    )

    assert payload["metadata"]["mode"] == "smn_only_fallback"
    assert payload["forecast"]["will_rain"] is True
    assert payload["decision"]["recommended_guard"] == "preventiva"
