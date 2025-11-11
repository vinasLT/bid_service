from fastapi import APIRouter

from app.routers.v1.bid.admin import admin_bids_router
from app.routers.v1.bid.user import user_bids_router
from app.routers.v1.health import health_router

private_router = APIRouter(prefix='/private/v1')

private_router.include_router(admin_bids_router)
private_router.include_router(user_bids_router)
private_router.include_router(health_router)
