from fastapi import APIRouter

from app.routers.v1.bid.admin import bids_management_router
from app.routers.v1.bid.user import user_bids_router
from app.routers.v1.health import health_router

private_router = APIRouter(prefix='/private/v1')

private_router.include_router(bids_management_router)
private_router.include_router(user_bids_router)
