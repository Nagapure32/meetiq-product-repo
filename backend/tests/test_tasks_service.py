import asyncio

import pytest
from fastapi import HTTPException


class FakeSupabaseGateway:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {
            "tasks": [],
            "task_assignees": [],
            "profiles": [],
            "meetings": [],
        }
        self.deleted: list[tuple[str, dict]] = []

    async def get(self, path: str, params: dict | None = None) -> list[dict]:
        rows = [row.copy() for row in self.tables[path]]
        if not params:
            return rows

        for key, value in params.items():
            if key in {"select", "order", "limit", "or"}:
                continue
            if isinstance(value, str) and value.startswith("eq."):
                expected = value[3:]
                rows = [row for row in rows if str(row.get(key)) == expected]
            if isinstance(value, str) and value.startswith("in.("):
                expected_values = value[4:-1].split(",")
                rows = [row for row in rows if str(row.get(key)) in expected_values]

        return rows

    async def insert(self, path: str, payload: dict | list[dict]) -> list[dict]:
        payloads = payload if isinstance(payload, list) else [payload]
        rows = []
        for item in payloads:
            row = item.copy()
            row.setdefault("id", f"{path}-{len(self.tables[path]) + 1}")
            self.tables[path].append(row)
            rows.append(row.copy())
        return rows

    async def patch(self, path: str, payload: dict, params: dict) -> list[dict]:
        rows = await self.get(path, params)
        patched = []
        ids = {row["id"] for row in rows}
        for row in self.tables[path]:
            if row.get("id") in ids:
                row.update(payload)
                patched.append(row.copy())
        return patched

    async def delete(self, path: str, params: dict) -> list[dict]:
        rows = await self.get(path, params)
        ids = {row["id"] for row in rows}
        self.tables[path] = [row for row in self.tables[path] if row.get("id") not in ids]
        self.deleted.append((path, params))
        return rows


def run(coro):
    return asyncio.run(coro)


def test_create_task_stores_multiple_assignees(monkeypatch):
    from app.api.v1.schemas import TaskCreate
    from app.services import tasks

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(tasks, "supabase_gateway", fake)
    monkeypatch.setattr(tasks, "get_dev_user_id", lambda: "owner-1")

    result = run(
        tasks.create_user_task(
            TaskCreate(
                title="Prepare client demo",
                description="Build demo data and screenshots",
                status="todo",
                priority="high",
                due_date="2026-05-24",
                assignee_user_ids=["user-1", "user-2"],
            )
        )
    )

    assert result["title"] == "Prepare client demo"
    assert result["owner_user_id"] == "owner-1"
    assert result["assignee_user_id"] == "user-1"
    assert [assignee["user_id"] for assignee in fake.tables["task_assignees"]] == [
        "user-1",
        "user-2",
    ]


def test_create_task_rejects_non_iso_due_date(monkeypatch):
    from app.api.v1.schemas import TaskCreate
    from app.services import tasks

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(tasks, "supabase_gateway", fake)
    monkeypatch.setattr(tasks, "get_dev_user_id", lambda: "owner-1")

    with pytest.raises(HTTPException) as exc:
        run(
            tasks.create_user_task(
                TaskCreate(
                    title="Prepare client demo",
                    status="todo",
                    priority="high",
                    due_date="Monday",
                    assignee_user_ids=[],
                )
            )
        )

    assert exc.value.status_code == 422
    assert "YYYY-MM-DD" in exc.value.detail
    assert fake.tables["tasks"] == []


def test_list_tasks_returns_assignee_profiles(monkeypatch):
    from app.services import tasks

    fake = FakeSupabaseGateway()
    fake.tables["tasks"] = [
        {
            "id": "task-1",
            "owner_user_id": "owner-1",
            "assignee_user_id": "user-1",
            "title": "Prepare client demo",
            "description": None,
            "status": "in_progress",
            "priority": "high",
            "due_date": "2026-05-24",
            "meeting_id": "meeting-1",
            "action_item_id": None,
            "created_at": "2026-05-19T08:00:00Z",
            "updated_at": "2026-05-19T08:00:00Z",
        }
    ]
    fake.tables["task_assignees"] = [
        {"id": "ta-1", "task_id": "task-1", "user_id": "user-1", "role": "primary"},
        {"id": "ta-2", "task_id": "task-1", "user_id": "user-2", "role": "collaborator"},
    ]
    fake.tables["profiles"] = [
        {"id": "user-1", "display_name": "Ravi Sharma", "email": "ravi@example.com"},
        {"id": "user-2", "display_name": "Priya Kale", "email": "priya@example.com"},
    ]
    monkeypatch.setattr(tasks, "supabase_gateway", fake)
    monkeypatch.setattr(tasks, "get_dev_user_id", lambda: "owner-1")

    result = run(tasks.list_user_tasks())

    assert result[0]["assignees"] == [
        {
            "user_id": "user-1",
            "display_name": "Ravi Sharma",
            "email": "ravi@example.com",
            "role": "primary",
        },
        {
            "user_id": "user-2",
            "display_name": "Priya Kale",
            "email": "priya@example.com",
            "role": "collaborator",
        },
    ]


def test_list_tasks_returns_linked_meeting_context(monkeypatch):
    from app.services import tasks

    fake = FakeSupabaseGateway()
    fake.tables["tasks"] = [
        {
            "id": "task-1",
            "owner_user_id": "owner-1",
            "assignee_user_id": None,
            "title": "Share pricing notes",
            "description": "Send the follow-up from the roadmap call",
            "status": "todo",
            "priority": "medium",
            "due_date": "2026-05-24",
            "meeting_id": "meeting-1",
            "action_item_id": "action-1",
            "created_at": "2026-05-19T08:00:00Z",
            "updated_at": "2026-05-19T08:00:00Z",
        }
    ]
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "owner-1",
            "subject": "Roadmap sync",
            "start_time": "2026-05-19T10:00:00Z",
            "end_time": "2026-05-19T10:30:00Z",
            "organizer_email": "pm@example.com",
        }
    ]
    monkeypatch.setattr(tasks, "supabase_gateway", fake)
    monkeypatch.setattr(tasks, "get_dev_user_id", lambda: "owner-1")

    result = run(tasks.list_user_tasks())

    assert result[0]["meeting"] == {
        "id": "meeting-1",
        "subject": "Roadmap sync",
        "start_time": "2026-05-19T10:00:00Z",
        "end_time": "2026-05-19T10:30:00Z",
        "organizer_email": "pm@example.com",
    }


def test_update_task_replaces_assignees_and_status(monkeypatch):
    from app.api.v1.schemas import TaskUpdate
    from app.services import tasks

    fake = FakeSupabaseGateway()
    fake.tables["tasks"] = [
        {
            "id": "task-1",
            "owner_user_id": "owner-1",
            "assignee_user_id": "user-1",
            "title": "Prepare client demo",
            "description": None,
            "status": "todo",
            "priority": "medium",
        }
    ]
    fake.tables["task_assignees"] = [
        {"id": "ta-1", "task_id": "task-1", "user_id": "user-1", "role": "primary"}
    ]
    monkeypatch.setattr(tasks, "supabase_gateway", fake)
    monkeypatch.setattr(tasks, "get_dev_user_id", lambda: "owner-1")

    result = run(
        tasks.update_user_task(
            "task-1",
            TaskUpdate(status="done", priority="low", assignee_user_ids=["user-2", "user-3"]),
        )
    )

    assert result["status"] == "done"
    assert result["priority"] == "low"
    assert result["assignee_user_id"] == "user-2"
    assert [assignee["user_id"] for assignee in fake.tables["task_assignees"]] == [
        "user-2",
        "user-3",
    ]


def test_delete_task_removes_owned_task(monkeypatch):
    from app.services import tasks

    fake = FakeSupabaseGateway()
    fake.tables["tasks"] = [{"id": "task-1", "owner_user_id": "owner-1", "title": "Delete me"}]
    fake.tables["task_assignees"] = [
        {"id": "ta-1", "task_id": "task-1", "user_id": "user-1", "role": "primary"}
    ]
    monkeypatch.setattr(tasks, "supabase_gateway", fake)
    monkeypatch.setattr(tasks, "get_dev_user_id", lambda: "owner-1")

    run(tasks.delete_user_task("task-1"))

    assert fake.tables["tasks"] == []
    assert fake.tables["task_assignees"] == []
