from fastapi import APIRouter

from app.api.v1.schemas import DashboardOverview
from app.services.dashboard import get_dashboard_overview

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=DashboardOverview)
async def get_analytics_overview() -> DashboardOverview:
    return await get_dashboard_overview()
