import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.db.supabase import supabase_gateway
from app.services.assignee_resolution import (
    AssigneeResolution,
    is_first_person_assignee,
    resolve_assignee,
)
from app.services.task_email import TaskEmailResult, send_task_assignment_email

VALID_PRIORITIES = {"low", "medium", "high", "urgent"}
URGENT_PRIORITY_KEYWORDS = {
    "urgent",
    "asap",
    "immediately",
    "critical",
    "blocker",
    "blocked",
    "production issue",
}
HIGH_PRIORITY_KEYWORDS = {
    "client",
    "customer",
    "demo",
    "deadline",
    "escalation",
    "must",
    "important",
}
LOW_PRIORITY_KEYWORDS = {
    "optional",
    "nice to have",
    "if possible",
    "whenever",
    "later",
}
URGENT_TIME_KEYWORDS = {
    "today",
    "tonight",
    "eod",
    "end of day",
    "end-of-day",
}
HIGH_TIME_KEYWORDS = {
    "tomorrow",
    "next day",
    "next 2 days",
    "next two days",
}
WEEKDAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass(frozen=True)
class MeetingAITask:
    title: str
    description: str | None = None
    priority: str = "medium"
    due_date: str | None = None
    assignee_name: str | None = None
    evidence_segment_sequence: int | None = None


@dataclass(frozen=True)
class MeetingAIResult:
    summary: str
    key_points: list[str]
    decisions: list[str]
    tasks: list[MeetingAITask]


async def generate_meeting_intelligence(
    meeting_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    meeting = await _get_meeting_for_ai(meeting_id, user_id)
    transcript_segments = await _get_transcript_segments(meeting_id)
    if not transcript_segments:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Meeting has no transcript segments to analyze.",
        )

    ai_result = _run_agno_meeting_agent(meeting, transcript_segments)
    participants = await _get_meeting_participants(meeting_id)
    profiles = await _get_profiles_for_participants(participants)
    summary = await _store_summary(meeting_id, ai_result)
    action_items, created_count, skipped_action_items_count = await _store_action_items(
        meeting,
        transcript_segments,
        ai_result.tasks,
        participants,
        profiles,
    )
    tasks, skipped_tasks_count = await _store_tasks_for_calendar_user(meeting, action_items)

    return {
        "meeting_id": meeting_id,
        "summary": summary,
        "generated_tasks_count": len(ai_result.tasks),
        "created_action_items_count": created_count,
        "skipped_action_items_count": skipped_action_items_count,
        "created_tasks_count": len(tasks),
        "skipped_tasks_count": skipped_tasks_count,
        "tasks": tasks,
    }


async def _get_meeting_for_ai(meeting_id: str, user_id: str | None = None) -> dict[str, Any]:
    params = {
        "select": "id,user_id,subject,start_time,end_time,organizer_email,source_type",
        "id": f"eq.{meeting_id}",
        "limit": "1",
    }
    if user_id:
        params["user_id"] = f"eq.{user_id}"

    rows = await supabase_gateway.get(
        "meetings",
        params,
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    meeting = rows[0]
    if not meeting.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Meeting is missing a calendar user.",
        )
    return meeting


async def _get_transcript_segments(meeting_id: str) -> list[dict[str, Any]]:
    return await supabase_gateway.get(
        "transcript_segments",
        {
            "select": (
                "id,sequence,speaker,source_id,speaker_participant_id,speaker_aad_user_id,"
                "speaker_email,speaker_user_principal_name,text,created_at,started_at,ended_at"
            ),
            "meeting_id": f"eq.{meeting_id}",
            "order": "sequence.asc.nullslast,started_at.asc.nullslast,created_at.asc",
            "limit": "1000",
        },
    )


def _run_agno_meeting_agent(
    meeting: dict[str, Any],
    transcript_segments: list[dict[str, Any]],
) -> MeetingAIResult:
    if not settings.enable_ai_summaries:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI summaries are disabled. Set ENABLE_AI_SUMMARIES=true.",
        )
    if (
        not settings.azure_openai_api_key
        or not settings.azure_openai_endpoint
        or not settings.azure_openai_deployment
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure OpenAI is not configured.",
        )
    try:
        from agno.agent import Agent
        from agno.models.azure import AzureOpenAI
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agno is not installed. Install backend AI dependencies first.",
        ) from exc

    agent = Agent(
        model=AzureOpenAI(
            id=settings.azure_openai_deployment,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment,
        ),
        instructions=_meeting_agent_instructions(),
    )
    try:
        response = agent.run(_meeting_prompt(meeting, transcript_segments))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Azure OpenAI request failed. Check AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_DEPLOYMENT, and AZURE_OPENAI_API_VERSION. "
                f"Configured deployment: {settings.azure_openai_deployment}. "
                f"Provider error: {exc}"
            ),
        ) from exc

    content = getattr(response, "content", response)
    if not content or str(content).strip().lower() in {"none", "null"}:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Azure OpenAI did not return usable content. Check that "
                f"deployment '{settings.azure_openai_deployment}' exists on "
                "the configured Azure OpenAI endpoint."
            ),
        )
    return _parse_ai_result(str(content))


def _meeting_agent_instructions() -> list[str]:
    return [
        "You identify meeting outcomes for a productivity app.",
        "Return only valid JSON with keys: summary, key_points, decisions, tasks.",
        (
            "Extract every explicit action item from the transcript, including "
            "commitments, requests, follow-ups, blockers to resolve, documents to send, "
            "updates to provide, decisions that require execution, and owner-specific next steps."
        ),
        (
            "Do not skip a task only because the due date is missing. Use null for due_date "
            "when the transcript gives no clear date."
        ),
        (
            "Do not skip a task only because the assignee is unclear. Use null for "
            "assignee_name when the transcript does not say who owns the work."
        ),
        (
            "tasks must be an array of objects with title, description, priority, "
            "due_date, assignee_name, evidence_segment_sequence."
        ),
        (
            "Resolve relative dates using the meeting date shown in the prompt. Do not use "
            "an old training-data year. If the meeting is in 2026, returned due dates must "
            "also be in 2026 unless the transcript clearly says another year."
        ),
        (
            "assignee_name must be the person who accepted or was assigned the work. "
            "Use I/me when the speaker assigned work to themselves."
        ),
        (
            "evidence_segment_sequence must be the transcript segment sequence number "
            "that proves the assignment."
        ),
        (
            "Do not invent assignees. Use null for assignee_name when the transcript "
            "does not say who owns the work."
        ),
        "priority must be one of low, medium, high, urgent.",
        (
            "Use urgent for due today, overdue work, blockers, ASAP/immediate work, "
            "critical issues, and production issues."
        ),
        (
            "Use high for work due within two days, client/customer commitments, demos, "
            "deadlines, escalations, must-do items, and important follow-ups."
        ),
        (
            "Use low only for optional, nice-to-have, if-possible, whenever, or later work "
            "when no urgent or high signal exists."
        ),
        (
            "Infer priority even when the speaker does not explicitly say low, medium, "
            "high, or urgent. Use due date, timing words, stakeholder impact, blockers, "
            "and business context to choose the priority."
        ),
        "Use medium for normal assigned work when no stronger priority signal exists.",
        "Use null for due_date unless the transcript gives a clear date.",
        "When due_date is present, return it as YYYY-MM-DD only.",
    ]


def _meeting_prompt(meeting: dict[str, Any], transcript_segments: list[dict[str, Any]]) -> str:
    transcript = "\n".join(
        (
            f"[{segment.get('sequence')}] "
            f"{segment.get('speaker') or 'Unknown speaker'}: {segment.get('text') or ''}"
        )
        for segment in transcript_segments
    )
    return (
        f"Meeting subject: {meeting.get('subject') or 'Untitled meeting'}\n\n"
        f"Meeting start time: {meeting.get('start_time') or 'Unknown'}\n\n"
        "Transcript:\n"
        f"{transcript}"
    )


def _parse_ai_result(content: str) -> MeetingAIResult:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        preview = cleaned[:240] if cleaned else "<empty>"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "AI response was not valid JSON. Check the Azure OpenAI deployment "
                f"and model output. Response preview: {preview}"
            ),
        ) from exc
    tasks = [
        MeetingAITask(
            title=str(task.get("title", "")).strip(),
            description=task.get("description"),
            priority=_normalize_priority(task.get("priority")),
            due_date=task.get("due_date"),
            assignee_name=task.get("assignee_name"),
            evidence_segment_sequence=_parse_optional_int(task.get("evidence_segment_sequence")),
        )
        for task in data.get("tasks", [])
        if str(task.get("title", "")).strip()
    ]
    return MeetingAIResult(
        summary=str(data.get("summary") or ""),
        key_points=[str(item) for item in data.get("key_points", [])],
        decisions=[str(item) for item in data.get("decisions", [])],
        tasks=tasks,
    )


async def _store_summary(meeting_id: str, ai_result: MeetingAIResult) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    rows = await supabase_gateway.upsert(
        "meeting_summaries",
        {
            "meeting_id": meeting_id,
            "summary": ai_result.summary,
            "key_points": ai_result.key_points,
            "decisions": ai_result.decisions,
            "model": f"agno:{settings.azure_openai_deployment}",
            "updated_at": now,
        },
        on_conflict="meeting_id",
    )
    return rows[0] if rows else {"meeting_id": meeting_id, "summary": ai_result.summary}


async def _store_action_items(
    meeting: dict[str, Any],
    transcript_segments: list[dict[str, Any]],
    ai_tasks: list[MeetingAITask],
    participants: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    if not ai_tasks:
        return [], 0, 0

    existing_by_title = await _existing_by_title("action_items", meeting["id"])
    payloads = []
    action_items = []
    skipped_count = 0
    for task in ai_tasks:
        existing = existing_by_title.get(_normalize_title(task.title))
        if existing:
            enriched_existing = await _enrich_action_item_assignee(
                existing,
                task,
                transcript_segments,
                participants,
                profiles,
            )
            action_items.append(enriched_existing)
            skipped_count += 1
            continue
        evidence_segment, resolution = _resolve_task_assignee(
            task,
            transcript_segments,
            participants,
            profiles,
        )
        due_date = _normalize_due_date(task.due_date, meeting.get("start_time"))
        priority = _calculate_task_priority(
            ai_priority=task.priority,
            due_date=due_date,
            reference_time=meeting.get("start_time"),
            evidence_segment=evidence_segment,
            title=task.title,
            description=task.description,
        )
        payloads.append(
            {
                "meeting_id": meeting["id"],
                "assignee_user_id": resolution.user_id,
                "assignee_display_name": resolution.display_name or task.assignee_name,
                "assignee_email": resolution.email,
                "assignee_resolution_status": resolution.status,
                "assignee_resolution_confidence": resolution.confidence,
                "assignee_resolution_reason": resolution.reason,
                "title": task.title,
                "description": task.description,
                "status": "open",
                "priority": priority,
                "due_date": due_date,
                "source_transcript_segment_id": (
                    evidence_segment.get("id") if evidence_segment else None
                ),
            }
        )
    created = await supabase_gateway.insert("action_items", payloads) if payloads else []
    return [*action_items, *created], len(created), skipped_count


def _resolve_task_assignee(
    task: MeetingAITask,
    transcript_segments: list[dict[str, Any]],
    participants: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    assignee_name_override: str | None = None,
) -> tuple[dict[str, Any] | None, Any]:
    assignee_name = assignee_name_override or task.assignee_name
    evidence_segment = _find_evidence_segment(
        transcript_segments,
        task.evidence_segment_sequence,
        allow_missing_sequence_fallback=not is_first_person_assignee(assignee_name),
    )
    assignee_name = assignee_name or _infer_assignee_from_evidence_text(
        evidence_segment,
        participants,
    )
    resolution = resolve_assignee(
        assignee_name,
        evidence_segment,
        participants,
        profiles,
    )
    if resolution.status == "resolved" and not (assignee_name_override or task.assignee_name):
        resolution = AssigneeResolution(
            user_id=resolution.user_id,
            email=resolution.email,
            display_name=resolution.display_name,
            status=resolution.status,
            confidence=resolution.confidence,
            reason="evidence_text_participant_name",
        )
    return evidence_segment, resolution


def _infer_assignee_from_evidence_text(
    evidence_segment: dict[str, Any] | None,
    participants: list[dict[str, Any]],
) -> str | None:
    if not evidence_segment:
        return None

    text_tokens = set(_name_tokens(evidence_segment.get("text")))
    if not text_tokens:
        return None

    matches = []
    for participant in participants:
        display_name = participant.get("display_name")
        participant_tokens = _name_tokens(display_name)
        if not participant_tokens:
            continue

        strong_tokens = [token for token in participant_tokens if len(token) >= 3]
        if text_tokens.intersection(strong_tokens):
            matches.append(display_name)

    unique_matches = sorted({match for match in matches if match})
    return unique_matches[0] if len(unique_matches) == 1 else None


def _name_tokens(value: Any) -> list[str]:
    return [
        token
        for token in re.sub(r"[^a-z0-9@._'+-]+", " ", str(value or "").lower()).split()
        if token
    ]


async def _enrich_action_item_assignee(
    action_item: dict[str, Any],
    task: MeetingAITask,
    transcript_segments: list[dict[str, Any]],
    participants: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> dict[str, Any]:
    if action_item.get("assignee_email"):
        return action_item

    assignee_name = task.assignee_name or action_item.get("assignee_display_name")
    if not assignee_name:
        return action_item

    _, resolution = _resolve_task_assignee(
        task,
        transcript_segments,
        participants,
        profiles,
        assignee_name_override=assignee_name,
    )
    if not resolution.email:
        return action_item

    update_payload = {
        "assignee_user_id": resolution.user_id,
        "assignee_display_name": resolution.display_name or assignee_name,
        "assignee_email": resolution.email,
        "assignee_resolution_status": resolution.status,
        "assignee_resolution_confidence": resolution.confidence,
        "assignee_resolution_reason": resolution.reason,
    }
    rows = await supabase_gateway.patch(
        "action_items",
        update_payload,
        params={"id": f"eq.{action_item['id']}", "limit": "1"},
    )
    if rows:
        return rows[0]
    action_item.update(update_payload)
    return action_item


async def _store_tasks_for_calendar_user(
    meeting: dict[str, Any],
    action_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    if not action_items:
        return [], 0

    existing_by_title = await _existing_by_title("tasks", meeting["id"])
    now = datetime.now(UTC).isoformat()
    task_payloads = []
    assignee_names_by_action_item_id = {}
    skipped_count = 0
    is_uploaded_recording = meeting.get("source_type") == "uploaded_recording"
    for action_item in action_items:
        existing_task = existing_by_title.get(_normalize_title(action_item["title"]))
        if existing_task:
            await _enrich_existing_task_assignment(existing_task, action_item, meeting)
            skipped_count += 1
            continue
        action_item_id = action_item.get("id")
        if action_item_id:
            assignee_names_by_action_item_id[action_item_id] = action_item.get(
                "assignee_display_name"
            )
        task_payloads.append(
            {
                "owner_user_id": meeting["user_id"],
                "assignee_user_id": action_item.get("assignee_user_id"),
                "assignee_email": action_item.get("assignee_email"),
                "assignment_source": action_item.get("assignee_resolution_reason"),
                "notification_status": "not_required" if is_uploaded_recording else "not_sent",
                "meeting_id": meeting["id"],
                "action_item_id": action_item_id,
                "title": action_item["title"],
                "description": action_item.get("description"),
                "status": "todo",
                "priority": _normalize_priority(action_item.get("priority")),
                "due_date": _normalize_due_date(
                    action_item.get("due_date"),
                    meeting.get("start_time"),
                ),
                "created_at": now,
                "updated_at": now,
            }
        )
    tasks = await supabase_gateway.insert("tasks", task_payloads) if task_payloads else []
    if tasks:
        task_assignees = [
            {
                "task_id": task["id"],
                "user_id": task["assignee_user_id"],
                "role": "primary",
                "created_at": now,
            }
            for task in tasks
            if task.get("assignee_user_id")
        ]
        if task_assignees:
            await supabase_gateway.insert("task_assignees", task_assignees)
        for task in tasks:
            if is_uploaded_recording:
                continue
            await _send_task_email_if_needed(
                task,
                meeting,
                assignee_names_by_action_item_id.get(task.get("action_item_id")),
            )
    return tasks, skipped_count


async def _enrich_existing_task_assignment(
    task: dict[str, Any],
    action_item: dict[str, Any],
    meeting: dict[str, Any],
) -> None:
    update_payload = {}
    if not task.get("assignee_user_id") and action_item.get("assignee_user_id"):
        update_payload["assignee_user_id"] = action_item.get("assignee_user_id")
    if not task.get("assignee_email") and action_item.get("assignee_email"):
        update_payload["assignee_email"] = action_item.get("assignee_email")
    if not task.get("assignment_source") and action_item.get("assignee_resolution_reason"):
        update_payload["assignment_source"] = action_item.get("assignee_resolution_reason")

    if update_payload:
        rows = await supabase_gateway.patch(
            "tasks",
            update_payload,
            params={"id": f"eq.{task['id']}", "limit": "1"},
        )
        task.update(rows[0] if rows else update_payload)

    if meeting.get("source_type") == "uploaded_recording":
        await _mark_task_notification_status(task, "not_required")
        return

    await _send_task_email_if_needed(
        task,
        meeting,
        action_item.get("assignee_display_name"),
    )


async def _send_task_email_if_needed(
    task: dict[str, Any],
    meeting: dict[str, Any],
    assignee_name: str | None,
) -> None:
    if not task.get("assignee_email"):
        await _mark_task_notification_status(task, "missing_recipient")
        return
    if task.get("notification_status") == "sent":
        return

    email_result: TaskEmailResult = send_task_assignment_email(
        to_email=task.get("assignee_email"),
        assignee_name=assignee_name or task.get("assignee_email"),
        task=task,
        meeting=meeting,
    )
    update_payload = {
        "notification_status": "sent" if email_result.sent else email_result.reason,
        "notification_error": email_result.error,
    }
    if email_result.sent:
        update_payload["notification_sent_at"] = datetime.now(UTC).isoformat()
    await supabase_gateway.patch(
        "tasks",
        update_payload,
        params={"id": f"eq.{task['id']}", "limit": "1"},
    )
    task.update(update_payload)


async def _mark_task_notification_status(task: dict[str, Any], status_value: str) -> None:
    if task.get("notification_status") == status_value:
        return
    update_payload = {"notification_status": status_value}
    await supabase_gateway.patch(
        "tasks",
        update_payload,
        params={"id": f"eq.{task['id']}", "limit": "1"},
    )
    task.update(update_payload)


async def _existing_by_title(path: str, meeting_id: str) -> dict[str, dict[str, Any]]:
    rows = await supabase_gateway.get(
        path,
        {
            "select": "*",
            "meeting_id": f"eq.{meeting_id}",
        },
    )
    return {_normalize_title(row.get("title")): row for row in rows if row.get("title")}


def _normalize_title(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _normalize_priority(value: Any) -> str:
    priority = str(value or "medium").lower()
    return priority if priority in VALID_PRIORITIES else "medium"


def _calculate_task_priority(
    ai_priority: Any,
    due_date: Any,
    reference_time: Any,
    evidence_segment: dict[str, Any] | None,
    title: str | None,
    description: str | None,
) -> str:
    text = _priority_text(evidence_segment, title, description)
    reference_date = _parse_reference_date(reference_time)
    parsed_due_date = _parse_reference_date(due_date)

    if _is_due_today_or_overdue(parsed_due_date, reference_date):
        return "urgent"
    if _contains_priority_keyword(text, URGENT_PRIORITY_KEYWORDS):
        return "urgent"
    if _contains_priority_keyword(text, URGENT_TIME_KEYWORDS):
        return "urgent"
    if _is_due_within_days(parsed_due_date, reference_date, days=2):
        return "high"
    if _contains_priority_keyword(text, HIGH_PRIORITY_KEYWORDS):
        return "high"
    if _contains_priority_keyword(text, HIGH_TIME_KEYWORDS):
        return "high"
    if _contains_priority_keyword(text, LOW_PRIORITY_KEYWORDS):
        return "low"

    return _normalize_priority(ai_priority)


def _priority_text(
    evidence_segment: dict[str, Any] | None,
    title: str | None,
    description: str | None,
) -> str:
    return " ".join(
        str(value or "").lower()
        for value in [
            title,
            description,
            (evidence_segment or {}).get("text"),
        ]
    )


def _contains_priority_keyword(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_due_today_or_overdue(
    due_date: date | None,
    reference_date: date | None,
) -> bool:
    return due_date is not None and reference_date is not None and due_date <= reference_date


def _is_due_within_days(
    due_date: date | None,
    reference_date: date | None,
    days: int,
) -> bool:
    if due_date is None or reference_date is None:
        return False
    days_until_due = (due_date - reference_date).days
    return 1 <= days_until_due <= days


def _normalize_due_date(value: Any, reference_time: Any = None) -> str | None:
    reference_date = _parse_reference_date(reference_time)
    if value is None:
        return None
    if isinstance(value, datetime):
        return _coerce_due_date_to_reference_year(value.date(), reference_date).isoformat()
    if isinstance(value, date):
        return _coerce_due_date_to_reference_year(value, reference_date).isoformat()

    clean = str(value).strip()
    if not clean or clean.lower() in {"none", "null", "n/a"}:
        return None

    try:
        parsed_date = date.fromisoformat(clean)
        return _coerce_due_date_to_reference_year(parsed_date, reference_date).isoformat()
    except ValueError:
        pass

    try:
        parsed_date = datetime.fromisoformat(clean.replace("Z", "+00:00")).date()
        return _coerce_due_date_to_reference_year(parsed_date, reference_date).isoformat()
    except ValueError:
        pass

    weekday = _parse_weekday_name(clean)
    if weekday is not None and reference_date is not None:
        days_until_due = (weekday - reference_date.weekday()) % 7
        if days_until_due == 0:
            days_until_due = 7
        return (reference_date + timedelta(days=days_until_due)).isoformat()

    return None


def _parse_weekday_name(value: str) -> int | None:
    normalized = " ".join(re.sub(r"[^a-z]+", " ", value.lower()).split())
    if normalized in WEEKDAY_NAMES:
        return WEEKDAY_NAMES[normalized]

    tokens = normalized.split()
    if len(tokens) == 2 and tokens[0] in {"on", "by", "before", "until"}:
        return WEEKDAY_NAMES.get(tokens[1])

    return None


def _parse_reference_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None


def _coerce_due_date_to_reference_year(
    due_date: date,
    reference_date: date | None,
) -> date:
    if reference_date is None or due_date >= reference_date:
        return due_date

    try:
        adjusted = due_date.replace(year=reference_date.year)
    except ValueError:
        return due_date

    if adjusted < reference_date:
        try:
            return adjusted.replace(year=reference_date.year + 1)
        except ValueError:
            return adjusted
    return adjusted


async def _get_meeting_participants(meeting_id: str) -> list[dict[str, Any]]:
    return await supabase_gateway.get(
        "meeting_participants",
        {"select": "*", "meeting_id": f"eq.{meeting_id}"},
    )


async def _get_profiles_for_participants(
    participants: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    emails = sorted(
        {
            (
                participant.get("email") or participant.get("user_principal_name") or ""
            ).strip().lower()
            for participant in participants
            if participant.get("email") or participant.get("user_principal_name")
        }
    )
    if not emails:
        return []
    return await supabase_gateway.get(
        "profiles",
        {"select": "id,display_name,email", "email": f"in.({','.join(emails)})"},
    )


def _find_evidence_segment(
    transcript_segments: list[dict[str, Any]],
    sequence: int | None,
    allow_missing_sequence_fallback: bool = True,
) -> dict[str, Any] | None:
    if sequence is None:
        if allow_missing_sequence_fallback:
            return transcript_segments[-1] if transcript_segments else None
        return None
    return next(
        (segment for segment in transcript_segments if segment.get("sequence") == sequence),
        None,
    )


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
