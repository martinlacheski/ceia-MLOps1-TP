from fastapi import APIRouter, Depends

from app.api.predictions.models import (
    GuardRecommendationRequest,
    GuardRecommendationResponse,
    LocalModelSignal,
    SmnSignal,
)
from app.core.dependencies import PermissionChecker


router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post(
    "/guard-recommendation",
    response_model=GuardRecommendationResponse,
    dependencies=[Depends(PermissionChecker("prediction:read"))],
)
def get_guard_recommendation(payload: GuardRecommendationRequest) -> GuardRecommendationResponse:
    # Stub intencional: permite cerrar el flujo end-to-end antes de conectar modelo, SMN y MLflow.
    local_model = LocalModelSignal(rain_probability=0.72, will_rain=True)
    smn = SmnSignal(
        reference_station="OBERA_AERO",
        daily_precipitation_mm=4.2,
        will_rain=True,
    )

    recommended_guard = "reforzada" if local_model.will_rain and smn.will_rain else "normal"

    return GuardRecommendationResponse(
        predicted_date=payload.target_date,
        local_model=local_model,
        smn=smn,
        recommended_guard=recommended_guard,
    )
