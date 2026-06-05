from datetime import UTC, datetime

from app.db.supabase import supabase_gateway


DEFAULT_MEETING_SETTINGS = {
    "auto_join_enabled": False,
    "require_approval": True,
    "approval_lead_minutes": 2,
    "look_ahead_minutes": 15,
    "join_early_seconds": 0,
    "max_late_join_minutes": 10,
    "leave_grace_minutes": 2,
    "use_service_hosted_media": False,
}


async def ensure_user_workspace(
    user_id: str,
    email: str | None,
    tenant_id: str | None = None,
    aad_user_id: str | None = None,
) -> dict[str, str]:
    calendar_status = "connected" if email else "pending"
    calendar_email = email or user_id

    await supabase_gateway.upsert(
        "profiles",
        {
            "id": user_id,
            "email": calendar_email,
        },
        on_conflict="id",
    )
    await supabase_gateway.upsert(
        "meeting_settings",
        {
            "user_id": user_id,
            **DEFAULT_MEETING_SETTINGS,
        },
        on_conflict="user_id",
    )
    await supabase_gateway.upsert(
        "calendar_connections",
        {
            "user_id": user_id,
            "provider": "microsoft",
            "tenant_id": tenant_id,
            "aad_user_id": aad_user_id,
            "email": calendar_email,
            "enabled": bool(email),
            "connection_status": calendar_status,
        },
        on_conflict="user_id,provider",
    )

    return {
        "user_id": user_id,
        "calendar_connection_status": calendar_status,
    }


async def get_onboarding_status(user_id: str) -> dict[str, object]:
    profile_rows = await supabase_gateway.get(
        "profiles",
        params={
            "select": "id,onboarding_completed_at",
            "id": f"eq.{user_id}",
            "limit": "1",
        },
    )
    calendar_rows = await supabase_gateway.get(
        "calendar_connections",
        params={
            "select": "connection_status",
            "user_id": f"eq.{user_id}",
            "provider": "eq.microsoft",
            "limit": "1",
        },
    )
    settings_rows = await supabase_gateway.get(
        "meeting_settings",
        params={
            "select": "auto_join_enabled",
            "user_id": f"eq.{user_id}",
            "limit": "1",
        },
    )

    onboarding_completed_at = profile_rows[0].get("onboarding_completed_at") if profile_rows else None
    calendar_connection_status = calendar_rows[0].get("connection_status") if calendar_rows else None
    auto_join_enabled = bool(settings_rows[0].get("auto_join_enabled")) if settings_rows else False

    return {
        "user_id": user_id,
        "onboarding_completed": bool(onboarding_completed_at),
        "onboarding_completed_at": onboarding_completed_at,
        "calendar_connection_status": calendar_connection_status,
        "auto_join_enabled": auto_join_enabled,
    }


async def complete_onboarding(user_id: str) -> dict[str, object]:
    completed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    await supabase_gateway.patch(
        "profiles",
        {"onboarding_completed_at": completed_at},
        params={"id": f"eq.{user_id}"},
    )
    return await get_onboarding_status(user_id)
