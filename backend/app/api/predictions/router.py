from pathlib import Path

from fastapi import APIRouter, Depends

from ceml_rain.inference import build_recommendation_payload
from app.api.predictions.models import (
    ForecastContext,
    ForecastSignal,
    GuardRecommendationRequest,
    GuardRecommendationResponse,
    OperationalDecision,
    PredictionContext,
    RainPredictionSignal,
    RecommendationMetadata,
)
from app.core.dependencies import PermissionChecker


router = APIRouter(prefix="/predictions", tags=["Predictions"])

DATA_ROOT = Path("/app/data") if Path("/app/data").exists() else Path("data")
SERVING_DIR = DATA_ROOT / "models" / "rain_t1" / "current"
TRAINING_DATASET_PATH = DATA_ROOT / "processed" / "rain_training_base.parquet"
SMN_DATA_PATH = DATA_ROOT / "processed" / "smn_pron5d_daily.jsonl"
TRAINING_SUMMARY_PATH = DATA_ROOT / "reports" / "rain_t1_training_summary.json"


@router.post(
    "/guard-recommendation",
    response_model=GuardRecommendationResponse,
    dependencies=[Depends(PermissionChecker("prediction:read"))],
)
def get_guard_recommendation(payload: GuardRecommendationRequest) -> GuardRecommendationResponse:
    recommendation = build_recommendation_payload(
        target_date=payload.target_date,
        serving_dir=SERVING_DIR,
        dataset_path=TRAINING_DATASET_PATH,
        smn_path=SMN_DATA_PATH,
        training_summary_path=TRAINING_SUMMARY_PATH,
    )
    prediction_data = recommendation["prediction"]
    forecast_data = recommendation["forecast"]
    decision_data = recommendation["decision"]
    metadata_data = recommendation["metadata"]

    return GuardRecommendationResponse(
        target_date=payload.target_date,
        prediction=RainPredictionSignal(**prediction_data),
        forecast=ForecastSignal(**forecast_data),
        decision=OperationalDecision(
            recommended_guard=decision_data["recommended_guard"],
            risk_level=decision_data["risk_level"],
            reason=decision_data["reason"],
        ),
        metadata=RecommendationMetadata(
            generated_at=metadata_data["generated_at"],
            mode=metadata_data["mode"],
            training_summary_path=metadata_data["training_summary_path"],
            serving_artifact_path=metadata_data["serving_artifact_path"],
            smn_data_path=metadata_data["smn_data_path"],
            degradation_reasons=metadata_data["degradation_reasons"],
            prediction_context=PredictionContext(**metadata_data["prediction_context"]),
            forecast_context=ForecastContext(**metadata_data["forecast_context"]),
        ),
    )
