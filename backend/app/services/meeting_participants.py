from typing import Any

from app.db.supabase import supabase_gateway


async def list_meeting_participants(meeting_id: str) -> list[dict[str, Any]]:
    return await supabase_gateway.get(
        "meeting_participants",
        {
            "select": "*",
            "meeting_id": f"eq.{meeting_id}",
        },
    )
