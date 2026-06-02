from fastapi import APIRouter

from app.api.v1.router import router as v1_router
from app.internal.router import router as internal_router

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/api/v1")
api_router.include_router(internal_router, prefix="/internal")

