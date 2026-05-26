from datetime import date

from pydantic import BaseModel, Field


class GuardRecommendationRequest(BaseModel):
    target_date: date = Field(description="Fecha para la cual se quiere evaluar la guardia")


class LocalModelSignal(BaseModel):
    rain_probability: float
    will_rain: bool


class SmnSignal(BaseModel):
    reference_station: str
    daily_precipitation_mm: float
    will_rain: bool


class GuardRecommendationResponse(BaseModel):
    predicted_date: date
    local_model: LocalModelSignal
    smn: SmnSignal
    recommended_guard: str
