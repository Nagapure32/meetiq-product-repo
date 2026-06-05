from fastapi import APIRouter

from app.api.v1.schemas import UserBootstrapRequest, UserBootstrapResponse, UserOnboardingStatus
from app.auth.current_user import CurrentUser, require_current_user
from app.services.user_bootstrap import complete_onboarding, ensure_user_workspace, get_onboarding_status

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/bootstrap", response_model=UserBootstrapResponse)
async def bootstrap_user_workspace(
    payload: UserBootstrapRequest,
    current_user: CurrentUser = require_current_user,
) -> UserBootstrapResponse:
    result = await ensure_user_workspace(
        user_id=current_user.user_id,
        email=payload.email or current_user.email,
        tenant_id=payload.tenant_id,
        aad_user_id=payload.aad_user_id,
    )
    return UserBootstrapResponse(**result)


@router.get("/status", response_model=UserOnboardingStatus)
async def get_user_onboarding_status(
    current_user: CurrentUser = require_current_user,
) -> UserOnboardingStatus:
    result = await get_onboarding_status(current_user.user_id)
    return UserOnboardingStatus(**result)


@router.post("/complete", response_model=UserOnboardingStatus)
async def complete_user_onboarding(
    current_user: CurrentUser = require_current_user,
) -> UserOnboardingStatus:
    result = await complete_onboarding(current_user.user_id)
    return UserOnboardingStatus(**result)
