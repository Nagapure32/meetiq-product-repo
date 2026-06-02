import asyncio
from datetime import UTC, datetime, timedelta


class FakeSupabaseGateway:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        today_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        yesterday = (now - timedelta(days=1)).date().isoformat()
        tomorrow = (now + timedelta(days=1)).date().isoformat()

        self.tables: dict[str, list[dict]] = {
            "meetings": [
                {
                    "id": "meeting-1",
                    "user_id": "user-1",
                    "subject": "Product sync",
                    "start_time": today_start.isoformat(),
                    "end_time": (today_start + timedelta(minutes=30)).isoformat(),
                    "bot_status": "ready",
                    "approval_status": "approved",
                    "organizer_email": "pm@example.com",
                }
            ],
            "tasks": [
                {
                    "id": "task-1",
                    "owner_user_id": "user-1",
                    "assignee_user_id": None,
                    "title": "Send recap",
                    "status": "todo",
                    "priority": "high",
                    "due_date": yesterday,
                    "meeting_id": "meeting-1",
                    "created_at": now.isoformat(),
                },
                {
                    "id": "task-2",
                    "owner_user_id": "user-1",
                    "assignee_user_id": None,
                    "title": "Update roadmap",
                    "status": "done",
                    "priority": "medium",
                    "due_date": tomorrow,
                    "meeting_id": "meeting-1",
                    "created_at": now.isoformat(),
                },
            ],
            "meeting_approvals": [
                {
                    "id": "approval-1",
                    "user_id": "user-1",
                    "status": "pending",
                    "requested_at": now.isoformat(),
                }
            ],
            "transcript_segments": [{"id": "segment-1", "meetings": {"user_id": "user-1"}}],
            "bot_heartbeats": [
                {
                    "bot_instance_id": "bot-1",
                    "status": "ok",
                    "last_seen_at": now.isoformat(),
                    "version": "1.0.0",
                }
            ],
            "bot_events": [
                {
                    "id": "event-1",
                    "event_type": "meeting_join_succeeded",
                    "severity": "info",
                    "message": "Bot joined Product sync.",
                    "created_at": now.isoformat(),
                }
            ],
        }

    async def get(self, path: str, params: dict | None = None) -> list[dict]:
        rows = [row.copy() for row in self.tables[path]]
        if not params:
            return rows

        for key, value in params.items():
            if key in {"select", "order", "limit", "or", "meetings.user_id"}:
                continue
            if isinstance(value, str) and value.startswith("eq."):
                expected = value[3:]
                rows = [row for row in rows if str(row.get(key)) == expected]
            if isinstance(value, str) and value.startswith("neq."):
                expected = value[4:]
                rows = [row for row in rows if str(row.get(key)) != expected]
            if isinstance(value, str) and value.startswith("gte."):
                expected = value[4:]
                rows = [row for row in rows if str(row.get(key)) >= expected]
            if isinstance(value, str) and value.startswith("lt."):
                expected = value[3:]
                rows = [row for row in rows if str(row.get(key)) < expected]

        if params.get("limit"):
            rows = rows[: int(params["limit"])]
        return rows


def run(coro):
    return asyncio.run(coro)


def test_dashboard_overview_returns_personal_command_center_data(monkeypatch):
    from app.services import dashboard

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(dashboard, "supabase_gateway", fake)
    monkeypatch.setattr(dashboard, "get_dev_user_id", lambda: "user-1")

    result = run(dashboard.get_dashboard_overview())

    metrics = {metric.label: metric.value for metric in result.metrics}
    assert metrics["Meetings today"] == 1
    assert metrics["Open follow-ups"] == 1
    assert metrics["Overdue"] == 1
    assert metrics["Completion rate"] == "50%"
    assert result.task_summary["completed"] == 1
    assert result.task_summary["open"] == 1
    assert result.attention_items[0]["title"] == "Send recap"
    assert result.recent_activity[0]["message"] == "Bot joined Product sync."
