from fastapi import APIRouter

from app.api.v1.schemas import DashboardOverview
from app.auth.current_user import CurrentUser, require_current_user
from app.services.dashboard import get_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOverview)
async def get_dashboard(current_user: CurrentUser = require_current_user) -> DashboardOverview:
    return await get_dashboard_overview(current_user.user_id)
