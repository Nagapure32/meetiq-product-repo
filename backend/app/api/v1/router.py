from fastapi import APIRouter

from app.api.v1.routes import (
    analytics,
    approvals,
    dashboard,
    health,
    integrations,
    meetings,
    onboarding,
    settings,
    tasks,
)

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(dashboard.router)
router.include_router(settings.router)
router.include_router(onboarding.router)
router.include_router(meetings.router)
router.include_router(tasks.router)
router.include_router(approvals.router)
router.include_router(analytics.router)
router.include_router(integrations.router)
