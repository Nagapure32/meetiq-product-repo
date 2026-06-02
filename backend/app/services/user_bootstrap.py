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
