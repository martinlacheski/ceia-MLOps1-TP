from datetime import date, datetime

from pydantic import BaseModel, Field


class GuardRecommendationRequest(BaseModel):
    target_date: date = Field(description="Fecha para la cual se quiere evaluar la guardia")


class RainPredictionSignal(BaseModel):
    source: str
    model_name: str
    model_stage: str
    rain_probability: float
    threshold: float
    will_rain: bool


class ForecastSignal(BaseModel):
    source: str
    reference_station: str
    precipitation_mm: float
    will_rain: bool


class OperationalDecision(BaseModel):
    recommended_guard: str
    risk_level: str
    reason: str


class PredictionContext(BaseModel):
    feature_date: str | None
    modeled_target_date: str | None
    target_alignment: str
    serving_source: str


class ForecastContext(BaseModel):
    status: str
    selected_station_reason: str
    forecast_date: str | None
    forecast_steps: int | None


class RecommendationMetadata(BaseModel):
    generated_at: datetime
    mode: str
    training_summary_path: str
    serving_artifact_path: str
    smn_data_path: str
    degradation_reasons: list[str]
    prediction_context: PredictionContext
    forecast_context: ForecastContext


class GuardRecommendationResponse(BaseModel):
    target_date: date
    prediction: RainPredictionSignal
    forecast: ForecastSignal
    decision: OperationalDecision
    metadata: RecommendationMetadata
