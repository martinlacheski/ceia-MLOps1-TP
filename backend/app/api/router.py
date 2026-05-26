from fastapi import APIRouter

from app.api.auth.router import router as auth_router
from app.api.predictions.router import router as predictions_router


api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(predictions_router)
