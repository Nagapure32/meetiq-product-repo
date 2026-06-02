from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.api.v1.schemas import DashboardMetric, DashboardOverview
from app.db.supabase import supabase_gateway
from app.services.meeting_settings import get_dev_user_id


async def get_dashboard_overview(user_id: str | None = None) -> DashboardOverview:
    user_id = user_id or get_dev_user_id()
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    week_start = today_start - timedelta(days=today_start.weekday())
    week_end = week_start + timedelta(days=7)

    meetings_today = await _get_rows(
        "meetings",
        {
            "select": "id,subject,start_time,end_time,bot_status,approval_status,organizer_email",
            "user_id": f"eq.{user_id}",
            "start_time": f"gte.{today_start.isoformat()}",
            "end_time": f"lt.{tomorrow_start.isoformat()}",
            "order": "start_time.asc",
        },
    )
    meetings_this_week = await _get_rows(
        "meetings",
        {
            "select": "id,start_time,end_time",
            "user_id": f"eq.{user_id}",
            "start_time": f"gte.{week_start.isoformat()}",
            "end_time": f"lt.{week_end.isoformat()}",
        },
    )
    upcoming_meetings = await _get_rows(
        "meetings",
        {
            "select": "id,subject,start_time,end_time,bot_status,approval_status,organizer_email",
            "user_id": f"eq.{user_id}",
            "end_time": f"gte.{now.isoformat()}",
            "order": "start_time.asc",
            "limit": "5",
        },
    )
    all_tasks = await _get_rows(
        "tasks",
        {
            "select": "id,title,status,priority,due_date,meeting_id,created_at",
            "or": f"(owner_user_id.eq.{user_id},assignee_user_id.eq.{user_id})",
            "order": "created_at.desc",
            "limit": "1000",
        },
    )
    open_tasks = await _get_rows(
        "tasks",
        {
            "select": "id,title,status,priority,due_date,meeting_id",
            "or": f"(owner_user_id.eq.{user_id},assignee_user_id.eq.{user_id})",
            "status": "neq.done",
            "order": "created_at.desc",
            "limit": "5",
        },
    )
    pending_approvals = await _get_rows(
        "meeting_approvals",
        {
            "select": "id,status",
            "user_id": f"eq.{user_id}",
            "status": "eq.pending",
        },
    )
    transcript_segments = await _get_rows(
        "transcript_segments",
        {
            "select": "id,meetings!inner(user_id)",
            "meetings.user_id": f"eq.{user_id}",
            "limit": "1000",
        },
    )
    heartbeats = await _get_rows(
        "bot_heartbeats",
        {
            "select": "bot_instance_id,status,last_seen_at,version",
            "order": "last_seen_at.desc",
            "limit": "1",
        },
    )
    bot_events = await _get_rows(
        "bot_events",
        {
            "select": "id,event_type,severity,message,created_at",
            "order": "created_at.desc",
            "limit": "5",
        },
    )

    meeting_hours = _meeting_hours(meetings_this_week)
    bot_status = _format_bot_status(heartbeats[0] if heartbeats else None, now)
    task_summary = _task_summary(all_tasks, today_start)
    attention_items = _attention_items(all_tasks, pending_approvals, now)
    recent_activity = _recent_activity(bot_events, upcoming_meetings)

    return DashboardOverview(
        metrics=[
            DashboardMetric(
                label="Meetings today",
                value=len(meetings_today),
                helper=f"{len(upcoming_meetings)} upcoming",
            ),
            DashboardMetric(
                label="Open follow-ups",
                value=task_summary["open"],
                helper=f"{task_summary['created_today']} created today",
            ),
            DashboardMetric(
                label="Overdue",
                value=task_summary["overdue"],
                helper="Need attention",
            ),
            DashboardMetric(
                label="Completion rate",
                value=f"{task_summary['completion_rate']}%",
                helper=f"{task_summary['completed']} done",
            ),
        ],
        upcoming_meetings=upcoming_meetings,
        recent_action_items=open_tasks,
        bot_status=bot_status,
        task_summary={
            **task_summary,
            "weekly_meeting_hours": round(meeting_hours, 1),
            "meetings_this_week": len(meetings_this_week),
            "pending_approvals": len(pending_approvals),
            "transcript_segments": len(transcript_segments),
        },
        attention_items=attention_items,
        recent_activity=recent_activity,
    )


async def _get_rows(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return await supabase_gateway.get(path, params=params)
    except Exception:
        return []


def _meeting_hours(rows: list[dict[str, Any]]) -> float:
    total = 0.0
    for row in rows:
        start = _parse_datetime(row.get("start_time"))
        end = _parse_datetime(row.get("end_time"))
        if start and end and end > start:
            total += (end - start).total_seconds() / 3600
    return total


def _task_summary(rows: list[dict[str, Any]], today_start: datetime) -> dict[str, int]:
    open_count = 0
    completed = 0
    overdue = 0
    created_today = 0
    today_date = today_start.date()

    for row in rows:
        status = str(row.get("status") or "").lower()
        due_date = _parse_date(row.get("due_date"))
        created_at = _parse_datetime(row.get("created_at"))

        if status == "done":
            completed += 1
        else:
            open_count += 1
            if due_date and due_date < today_date:
                overdue += 1

        if created_at and created_at.date() == today_date:
            created_today += 1

    total = open_count + completed
    completion_rate = round((completed / total) * 100) if total else 0
    return {
        "open": open_count,
        "completed": completed,
        "overdue": overdue,
        "created_today": created_today,
        "completion_rate": completion_rate,
    }


def _attention_items(
    tasks: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    now: datetime,
) -> list[dict[str, str]]:
    today_date = now.date()
    items: list[dict[str, str]] = []

    for task in tasks:
        status = str(task.get("status") or "").lower()
        due_date = _parse_date(task.get("due_date"))
        if status != "done" and due_date and due_date < today_date:
            items.append(
                {
                    "id": task.get("id", ""),
                    "type": "task",
                    "title": task.get("title") or "Untitled task",
                    "detail": f"Due {due_date.isoformat()}",
                }
            )

    for approval in approvals:
        items.append(
            {
                "id": approval.get("id", ""),
                "type": "approval",
                "title": "Meeting approval waiting",
                "detail": "Review the pending bot join request.",
            }
        )

    return items[:5]


def _recent_activity(
    bot_events: list[dict[str, Any]],
    meetings: list[dict[str, Any]],
) -> list[dict[str, str]]:
    items = [
        {
            "id": event.get("id", ""),
            "type": event.get("event_type") or "bot_event",
            "message": event.get("message") or "Assistant activity recorded.",
            "created_at": event.get("created_at") or "",
        }
        for event in bot_events
    ]

    if items:
        return items

    return [
        {
            "id": meeting.get("id", ""),
            "type": "meeting",
            "message": f"{meeting.get('subject') or 'Meeting'} is on your schedule.",
            "created_at": meeting.get("start_time") or "",
        }
        for meeting in meetings[:5]
    ]


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _format_bot_status(row: dict[str, Any] | None, now: datetime) -> dict[str, str]:
    if not row:
        return {
            "status": "not_connected",
            "message": "No bot heartbeat has been recorded yet.",
        }

    last_seen = _parse_datetime(row.get("last_seen_at"))
    if not last_seen:
        return {
            "status": row.get("status") or "unknown",
            "message": "Bot heartbeat exists, but last_seen_at is unavailable.",
        }

    age_seconds = max(0, int((now - last_seen).total_seconds()))
    status = "online" if age_seconds <= 180 else "stale"
    return {
        "status": status,
        "message": (
            f"{row.get('bot_instance_id', 'Bot')} last checked in "
            f"{age_seconds // 60} min {age_seconds % 60} sec ago."
        ),
    }
