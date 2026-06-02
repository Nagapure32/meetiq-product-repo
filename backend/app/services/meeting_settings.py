from fastapi import HTTPException, status

from app.api.v1.schemas import MeetingAssistantSettings
from app.core.config import settings
from app.db.supabase import supabase_gateway


def get_dev_user_id() -> str:
    if not settings.dev_user_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DEV_USER_ID is not configured. Auth-backed user resolution is not implemented yet.",
        )
    return settings.dev_user_id


async def get_meeting_assistant_settings(user_id: str | None = None) -> MeetingAssistantSettings:
    user_id = user_id or get_dev_user_id()
    rows = await supabase_gateway.get(
        "meeting_settings",
        params={
            "select": "*",
            "user_id": f"eq.{user_id}",
            "limit": "1",
        },
    )

    if not rows:
        return MeetingAssistantSettings(user_id=user_id)

    row = rows[0]
    return MeetingAssistantSettings(
        user_id=row["user_id"],
        auto_join_enabled=row.get("auto_join_enabled", False),
        require_approval=row.get("require_approval", True),
        approval_lead_minutes=row.get("approval_lead_minutes", 2),
        look_ahead_minutes=row.get("look_ahead_minutes", 15),
        join_early_seconds=row.get("join_early_seconds", 0),
        max_late_join_minutes=row.get("max_late_join_minutes", 10),
        leave_grace_minutes=row.get("leave_grace_minutes", 2),
        use_service_hosted_media=row.get("use_service_hosted_media", False),
    )


async def update_meeting_assistant_settings(
    payload: MeetingAssistantSettings,
    user_id: str | None = None,
) -> MeetingAssistantSettings:
    user_id = user_id or get_dev_user_id()
    rows = await supabase_gateway.upsert(
        "meeting_settings",
        {
            "user_id": user_id,
            "auto_join_enabled": payload.auto_join_enabled,
            "require_approval": payload.require_approval,
            "approval_lead_minutes": payload.approval_lead_minutes,
            "look_ahead_minutes": payload.look_ahead_minutes,
            "join_early_seconds": payload.join_early_seconds,
            "max_late_join_minutes": payload.max_late_join_minutes,
            "leave_grace_minutes": payload.leave_grace_minutes,
            "use_service_hosted_media": payload.use_service_hosted_media,
        },
        on_conflict="user_id",
    )

    row = rows[0] if rows else {"user_id": user_id, **payload.model_dump()}
    return MeetingAssistantSettings(
        user_id=row["user_id"],
        auto_join_enabled=row.get("auto_join_enabled", payload.auto_join_enabled),
        require_approval=row.get("require_approval", payload.require_approval),
        approval_lead_minutes=row.get("approval_lead_minutes", payload.approval_lead_minutes),
        look_ahead_minutes=row.get("look_ahead_minutes", payload.look_ahead_minutes),
        join_early_seconds=row.get("join_early_seconds", payload.join_early_seconds),
        max_late_join_minutes=row.get("max_late_join_minutes", payload.max_late_join_minutes),
        leave_grace_minutes=row.get("leave_grace_minutes", payload.leave_grace_minutes),
        use_service_hosted_media=row.get(
            "use_service_hosted_media",
            payload.use_service_hosted_media,
        ),
    )
