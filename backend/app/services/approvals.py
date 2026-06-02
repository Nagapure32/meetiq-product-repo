from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.supabase import supabase_gateway
from app.internal.schemas import BotApprovalUpsertRequest
from app.services.meeting_settings import get_dev_user_id

BOT_ONLINE_SECONDS = 180
DECISION_TO_STATUS = {
    "approve": "approved",
    "approved": "approved",
    "reject": "rejected",
    "rejected": "rejected",
}


async def list_user_approvals(user_id: str | None = None) -> list[dict[str, Any]]:
    user_id = user_id or get_dev_user_id()
    approvals = await supabase_gateway.get(
        "meeting_approvals",
        params={
            "select": "*",
            "user_id": f"eq.{user_id}",
            "order": "requested_at.desc",
        },
    )
    meeting_ids = [row["meeting_id"] for row in approvals if row.get("meeting_id")]
    meetings = (
        await supabase_gateway.get(
            "meetings",
            params={
                "select": (
                    "id,subject,start_time,end_time,bot_status,"
                    "approval_status,organizer_email"
                ),
                "id": f"in.({','.join(meeting_ids)})",
            },
        )
        if meeting_ids
        else []
    )
    meetings_by_id = {meeting["id"]: meeting for meeting in meetings}
    return [
        {
            **_normalize_approval_row(row),
            "meeting": meetings_by_id.get(row.get("meeting_id")),
        }
        for row in approvals
    ]


async def upsert_bot_approval(payload: BotApprovalUpsertRequest) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    approval_payload = {
        "bot_approval_id": payload.bot_approval_id,
        "meeting_id": payload.meeting_id,
        "user_id": payload.user_id,
        "status": _normalize_status(payload.status),
        "requested_via": payload.requested_via,
        "expires_at": _isoformat(payload.expires_at),
        "updated_at": now,
    }
    rows = await supabase_gateway.upsert(
        "meeting_approvals",
        approval_payload,
        on_conflict="bot_approval_id",
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase did not return the upserted approval.",
        )

    approval = _normalize_approval_row(rows[0])
    await _update_meeting_approval_status(payload.meeting_id, approval["status"], now)
    return approval


async def decide_user_approval(
    approval_id: str,
    decision: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    normalized_decision = _normalize_decision(decision)
    user_id = user_id or get_dev_user_id()
    approval = await _get_user_approval(approval_id, user_id)

    if approval.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval has already been decided.",
        )
    bot_approval_id = approval.get("bot_approval_id")
    if not bot_approval_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval is not linked to an active bot request.",
        )
    if not await _is_bot_online():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bot is offline. Approval decisions can be made when the Teams bot reconnects.",
        )

    bot_result = await _call_bot_decision_endpoint(bot_approval_id, decision, user_id)
    decided_at = datetime.now(UTC).isoformat()
    final_status = _normalize_status(bot_result.get("status") or normalized_decision)
    patch_payload = {
        "status": final_status,
        "decided_at": decided_at,
        "decided_by": bot_result.get("decided_by") or user_id,
        "decided_via": bot_result.get("decided_via") or "meetiq",
        "updated_at": decided_at,
    }
    rows = await supabase_gateway.patch(
        "meeting_approvals",
        patch_payload,
        params={"id": f"eq.{approval_id}", "user_id": f"eq.{user_id}", "limit": "1"},
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found.")

    meeting_id = approval.get("meeting_id")
    if meeting_id:
        await _update_meeting_approval_status(meeting_id, final_status, decided_at)

    row = _normalize_approval_row(rows[0])
    meeting = await _get_meeting(row.get("meeting_id"))
    return {**row, "meeting": meeting}


async def _get_user_approval(approval_id: str, user_id: str) -> dict[str, Any]:
    rows = await supabase_gateway.get(
        "meeting_approvals",
        params={
            "select": "*",
            "id": f"eq.{approval_id}",
            "user_id": f"eq.{user_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found.")
    return _normalize_approval_row(rows[0])


async def _get_meeting(meeting_id: str | None) -> dict[str, Any] | None:
    if not meeting_id:
        return None
    rows = await supabase_gateway.get(
        "meetings",
        params={
            "select": "id,subject,start_time,end_time,bot_status,approval_status,organizer_email",
            "id": f"eq.{meeting_id}",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


async def _is_bot_online() -> bool:
    rows = await supabase_gateway.get(
        "bot_heartbeats",
        params={"select": "last_seen_at,status", "order": "last_seen_at.desc", "limit": "1"},
    )
    if not rows:
        return False
    last_seen = _parse_datetime(rows[0].get("last_seen_at"))
    if not last_seen:
        return False
    age_seconds = (datetime.now(UTC) - last_seen).total_seconds()
    return age_seconds <= BOT_ONLINE_SECONDS


async def _call_bot_decision_endpoint(
    bot_approval_id: str,
    decision: str,
    decided_by: str,
) -> dict[str, Any]:
    if not settings.teams_bot_base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TEAMS_BOT_BASE_URL is not configured.",
        )
    if not settings.bot_internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BOT_INTERNAL_API_KEY is not configured.",
        )

    url = (
        f"{settings.teams_bot_base_url.rstrip('/')}"
        f"/api/platform/approvals/{bot_approval_id}/decision"
    )
    payload = {
        "decision": decision,
        "decided_by": decided_by,
        "decided_via": "meetiq",
    }
    headers = {"Authorization": f"Bearer {settings.bot_internal_api_key}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The Teams bot did not accept the approval decision.",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The Teams bot did not accept the approval decision.",
        )

    data = response.json()
    return data if isinstance(data, dict) else {}


async def _update_meeting_approval_status(
    meeting_id: str,
    approval_status: str,
    updated_at: str,
) -> None:
    await supabase_gateway.patch(
        "meetings",
        {"approval_status": approval_status, "updated_at": updated_at},
        params={"id": f"eq.{meeting_id}", "limit": "1"},
    )


def _normalize_approval_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = row.copy()
    normalized["status"] = _normalize_status(normalized.get("status"))
    return normalized


def _normalize_decision(value: str) -> str:
    normalized = DECISION_TO_STATUS.get(value.lower())
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Decision must be approve or reject.",
        )
    return normalized


def _normalize_status(value: Any) -> str:
    status_value = str(value or "pending").strip().lower()
    return DECISION_TO_STATUS.get(status_value, status_value)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None
