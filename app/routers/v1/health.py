from fastapi import APIRouter

from app.schemas.health import HealthResponse


health_router = APIRouter()


@health_router.get("/health", response_model=HealthResponse, tags=["health"])
async def get_health() -> HealthResponse:
    return HealthResponse()
