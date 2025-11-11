import pytest

from app.routers.v1.health import get_health
from app.schemas.health import HealthResponse


@pytest.mark.asyncio
async def test_get_health_returns_ok_status():
    response = await get_health()

    assert isinstance(response, HealthResponse)
    assert response.status == "ok"
