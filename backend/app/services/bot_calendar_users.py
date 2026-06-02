from app.db.supabase import supabase_gateway
from app.internal.schemas import BotCalendarUser


async def list_enabled_calendar_users() -> list[BotCalendarUser]:
    rows = await supabase_gateway.get(
        "bot_calendar_users",
        params={
            "select": "*",
        },
    )

    users: list[BotCalendarUser] = []
    for row in rows:
        users.append(
            BotCalendarUser(
                user_id=row["user_id"],
                tenant_id=row.get("tenant_id"),
                aad_user_id=row.get("aad_user_id"),
                email=row["email"],
                auto_join_enabled=row.get("auto_join_enabled", True),
                require_approval=row.get("require_approval", True),
                look_ahead_minutes=row.get("look_ahead_minutes", 15),
                approval_lead_minutes=row.get("approval_lead_minutes", 2),
                join_early_seconds=row.get("join_early_seconds", 0),
                max_late_join_minutes=row.get("max_late_join_minutes", 10),
                leave_grace_minutes=row.get("leave_grace_minutes", 2),
            )
        )

    return users
