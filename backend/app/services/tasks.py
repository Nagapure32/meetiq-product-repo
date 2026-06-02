from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException, status

from app.api.v1.schemas import TaskCreate, TaskUpdate
from app.db.supabase import supabase_gateway
from app.services.meeting_settings import get_dev_user_id

VALID_STATUSES = {"todo", "in_progress", "blocked", "done"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


async def list_user_tasks(user_id: str | None = None) -> list[dict[str, Any]]:
    user_id = user_id or get_dev_user_id()
    owned_or_primary = await supabase_gateway.get(
        "tasks",
        params={
            "select": "*",
            "or": f"(owner_user_id.eq.{user_id},assignee_user_id.eq.{user_id})",
            "order": "created_at.desc",
        },
    )
    assigned_links = await _safe_get(
        "task_assignees",
        {
            "select": "task_id",
            "user_id": f"eq.{user_id}",
        },
    )
    assigned_task_ids = [row["task_id"] for row in assigned_links if row.get("task_id")]
    assigned_tasks = (
        await _safe_get(
            "tasks",
            {
                "select": "*",
                "id": f"in.({','.join(assigned_task_ids)})",
                "order": "created_at.desc",
            },
        )
        if assigned_task_ids
        else []
    )

    tasks_by_id = {row["id"]: row for row in [*owned_or_primary, *assigned_tasks]}
    return await _hydrate_tasks(list(tasks_by_id.values()), user_id)


async def create_user_task(payload: TaskCreate, user_id: str | None = None) -> dict[str, Any]:
    user_id = user_id or get_dev_user_id()
    _validate_status(payload.status)
    _validate_priority(payload.priority)
    assignee_user_ids = _normalize_assignee_ids(payload.assignee_user_ids)
    now = datetime.now(UTC).isoformat()

    rows = await supabase_gateway.insert(
        "tasks",
        {
            "owner_user_id": user_id,
            "assignee_user_id": assignee_user_ids[0] if assignee_user_ids else None,
            "meeting_id": payload.meeting_id,
            "action_item_id": payload.action_item_id,
            "title": payload.title.strip(),
            "description": payload.description,
            "status": payload.status,
            "priority": payload.priority,
            "due_date": _serialize_date(payload.due_date),
            "created_at": now,
            "updated_at": now,
        },
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase did not return the created task.",
        )

    task = rows[0]
    await _replace_assignees(task["id"], assignee_user_ids)
    return (await _hydrate_tasks([task], user_id))[0]


async def update_user_task(
    task_id: str,
    payload: TaskUpdate,
    user_id: str | None = None,
) -> dict[str, Any]:
    user_id = user_id or get_dev_user_id()
    existing = await _get_owned_task(task_id, user_id)
    update_payload = payload.model_dump(exclude_unset=True, exclude={"assignee_user_ids"})

    if "status" in update_payload and update_payload["status"] is not None:
        _validate_status(update_payload["status"])
    if "priority" in update_payload and update_payload["priority"] is not None:
        _validate_priority(update_payload["priority"])
    if "title" in update_payload and update_payload["title"] is not None:
        update_payload["title"] = update_payload["title"].strip()
    if "due_date" in update_payload:
        update_payload["due_date"] = _serialize_date(update_payload["due_date"])

    if payload.assignee_user_ids is not None:
        assignee_user_ids = _normalize_assignee_ids(payload.assignee_user_ids)
        update_payload["assignee_user_id"] = assignee_user_ids[0] if assignee_user_ids else None
    else:
        assignee_user_ids = None

    if update_payload:
        update_payload["updated_at"] = datetime.now(UTC).isoformat()
        rows = await supabase_gateway.patch(
            "tasks",
            update_payload,
            params={"id": f"eq.{task_id}", "owner_user_id": f"eq.{user_id}", "limit": "1"},
        )
        task = rows[0] if rows else {**existing, **update_payload}
    else:
        task = existing

    if assignee_user_ids is not None:
        await _replace_assignees(task_id, assignee_user_ids)

    return (await _hydrate_tasks([task], user_id))[0]


async def delete_user_task(task_id: str, user_id: str | None = None) -> None:
    user_id = user_id or get_dev_user_id()
    await _get_owned_task(task_id, user_id)
    await supabase_gateway.delete("task_assignees", params={"task_id": f"eq.{task_id}"})
    await supabase_gateway.delete(
        "tasks",
        params={"id": f"eq.{task_id}", "owner_user_id": f"eq.{user_id}"},
    )


async def _get_owned_task(task_id: str, user_id: str) -> dict[str, Any]:
    rows = await supabase_gateway.get(
        "tasks",
        params={
            "select": "*",
            "id": f"eq.{task_id}",
            "owner_user_id": f"eq.{user_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return rows[0]


async def _hydrate_tasks(tasks: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
    tasks_with_assignees = await _with_assignees(tasks)
    return await _with_meetings(tasks_with_assignees, user_id)


async def _with_assignees(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not tasks:
        return []

    task_ids = [task["id"] for task in tasks if task.get("id")]
    links = await _safe_get(
        "task_assignees",
        {
            "select": "*",
            "task_id": f"in.({','.join(task_ids)})",
            "order": "created_at.asc",
        },
    )
    user_ids = sorted({link["user_id"] for link in links if link.get("user_id")})
    profiles = (
        await _safe_get(
            "profiles",
            {
                "select": "id,display_name,email",
                "id": f"in.({','.join(user_ids)})",
            },
        )
        if user_ids
        else []
    )
    profiles_by_id = {profile["id"]: profile for profile in profiles}
    links_by_task: dict[str, list[dict[str, Any]]] = {}

    for link in links:
        task_id = link.get("task_id")
        user_id = link.get("user_id")
        if not task_id or not user_id:
            continue
        profile = profiles_by_id.get(user_id, {})
        links_by_task.setdefault(task_id, []).append(
            {
                "user_id": user_id,
                "display_name": profile.get("display_name"),
                "email": profile.get("email"),
                "role": link.get("role") or "collaborator",
            }
        )

    return [{**task, "assignees": links_by_task.get(task["id"], [])} for task in tasks]


async def _with_meetings(tasks: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
    meeting_ids = sorted({task["meeting_id"] for task in tasks if task.get("meeting_id")})
    if not meeting_ids:
        return [{**task, "meeting": None} for task in tasks]

    meetings = await _safe_get(
        "meetings",
        {
            "select": "id,subject,start_time,end_time,organizer_email",
            "id": f"in.({','.join(meeting_ids)})",
            "user_id": f"eq.{user_id}",
        },
    )
    meetings_by_id = {
        meeting["id"]: {
            "id": meeting["id"],
            "subject": meeting.get("subject") or "Untitled meeting",
            "start_time": meeting.get("start_time"),
            "end_time": meeting.get("end_time"),
            "organizer_email": meeting.get("organizer_email"),
        }
        for meeting in meetings
        if meeting.get("id")
    }

    return [{**task, "meeting": meetings_by_id.get(task.get("meeting_id"))} for task in tasks]


async def _replace_assignees(task_id: str, assignee_user_ids: list[str]) -> None:
    await supabase_gateway.delete("task_assignees", params={"task_id": f"eq.{task_id}"})
    if not assignee_user_ids:
        return

    await supabase_gateway.insert(
        "task_assignees",
        [
            {
                "task_id": task_id,
                "user_id": user_id,
                "role": "primary" if index == 0 else "collaborator",
            }
            for index, user_id in enumerate(assignee_user_ids)
        ],
    )


async def _safe_get(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return await supabase_gateway.get(path, params=params)
    except Exception:
        return []


def _normalize_assignee_ids(user_ids: list[str]) -> list[str]:
    normalized = []
    seen = set()
    for user_id in user_ids:
        clean = user_id.strip()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized


def _validate_status(value: str) -> None:
    if value not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid status.",
        )


def _validate_priority(value: str) -> None:
    if value not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid priority.",
        )


def _serialize_date(value: str | date | None) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    try:
        return date.fromisoformat(normalized).isoformat()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid due_date. Use YYYY-MM-DD.",
        ) from exc
