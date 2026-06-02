from fastapi import APIRouter

from app.api.v1.schemas import ApprovalItem
from app.auth.current_user import CurrentUser, require_current_user
from app.services.approvals import decide_user_approval, list_user_approvals

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=dict[str, list[ApprovalItem]])
async def list_approvals(current_user: CurrentUser = require_current_user) -> dict[str, list]:
    return {"items": await list_user_approvals(current_user.user_id)}


@router.post("/{approval_id}/approve", response_model=ApprovalItem)
async def approve_approval(
    approval_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict:
    return await decide_user_approval(approval_id, "approve", current_user.user_id)


@router.post("/{approval_id}/reject", response_model=ApprovalItem)
async def reject_approval(
    approval_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict:
    return await decide_user_approval(approval_id, "reject", current_user.user_id)
