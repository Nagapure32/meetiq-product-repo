from typing import Any

from app.db.supabase import supabase_gateway
from app.services.meeting_settings import get_dev_user_id


async def list_user_meetings(
    transcript_ready: bool = False,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    user_id = user_id or get_dev_user_id()
    meetings = await _safe_get(
        "meetings",
        {
            "select": (
                "id,graph_event_id,subject,organizer_email,join_url,start_time,end_time,"
                "status,bot_status,approval_status,source_type,processing_status,"
                "uploaded_media_url,created_at,updated_at"
            ),
            "user_id": f"eq.{user_id}",
            "order": "start_time.desc",
            "limit": "100",
        },
    )
    meetings_with_counts = await _with_transcript_counts(meetings)
    if transcript_ready:
        return [
            meeting
            for meeting in meetings_with_counts
            if meeting.get("transcript_segment_count", 0) > 0
        ]
    return meetings_with_counts


async def get_user_meeting(meeting_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    user_id = user_id or get_dev_user_id()
    rows = await _safe_get(
        "meetings",
        {
            "select": (
                "id,graph_event_id,subject,organizer_email,join_url,start_time,end_time,"
                "status,bot_status,approval_status,source_type,processing_status,"
                "uploaded_media_url,created_at,updated_at"
            ),
            "id": f"eq.{meeting_id}",
            "user_id": f"eq.{user_id}",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


async def list_meeting_transcript(
    meeting_id: str,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    if not await get_user_meeting(meeting_id, user_id):
        return []
    return await _safe_get(
        "transcript_segments",
        {
            "select": "id,sequence,speaker,source_id,language,text,started_at,ended_at,created_at",
            "meeting_id": f"eq.{meeting_id}",
            "order": "sequence.asc.nullslast,started_at.asc.nullslast,created_at.asc",
            "limit": "1000",
        },
    )


async def get_meeting_summary(
    meeting_id: str,
    user_id: str | None = None,
) -> dict[str, Any] | None:
    if not await get_user_meeting(meeting_id, user_id):
        return None
    rows = await _safe_get(
        "meeting_summaries",
        {
            "select": "id,summary,key_points,decisions,model,created_at,updated_at",
            "meeting_id": f"eq.{meeting_id}",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


async def list_meeting_tasks(
    meeting_id: str,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    user_id = user_id or get_dev_user_id()
    return await _safe_get(
        "tasks",
        {
            "select": (
                "id,title,description,status,priority,due_date,meeting_id,action_item_id,"
                "created_at,updated_at"
            ),
            "meeting_id": f"eq.{meeting_id}",
            "owner_user_id": f"eq.{user_id}",
            "order": "created_at.desc",
        },
    )

async def _safe_get(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return await supabase_gateway.get(path, params=params)
    except Exception:
        return []


async def _with_transcript_counts(meetings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not meetings:
        return []

    meeting_ids = [str(meeting["id"]) for meeting in meetings if meeting.get("id")]
    if not meeting_ids:
        return [{**meeting, "transcript_segment_count": 0} for meeting in meetings]

    segments = await _safe_get(
        "transcript_segments",
        {
            "select": "meeting_id",
            "meeting_id": f"in.({','.join(meeting_ids)})",
        },
    )
    counts: dict[str, int] = {}
    for segment in segments:
        meeting_id = str(segment.get("meeting_id") or "")
        if meeting_id:
            counts[meeting_id] = counts.get(meeting_id, 0) + 1

    return [
        {
            **meeting,
            "transcript_segment_count": counts.get(str(meeting.get("id")), 0),
        }
        for meeting in meetings
    ]
