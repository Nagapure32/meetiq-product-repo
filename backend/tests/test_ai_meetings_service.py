import asyncio

import pytest
from fastapi import HTTPException


class FakeSupabaseGateway:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {
            "meetings": [],
            "transcript_segments": [],
            "profiles": [],
            "meeting_participants": [],
            "meeting_summaries": [],
            "action_items": [],
            "tasks": [],
            "task_assignees": [],
        }
    print("   ")
    async def get(self, path: str, params: dict | None = None) -> list[dict]:
        rows = [row.copy() for row in self.tables[path]]
        if not params:
            return rows

        for key, value in params.items():
            if key in {"select", "order", "limit"}:
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

    async def upsert(
        self,
        path: str,
        payload: dict,
        on_conflict: str | None = None,
    ) -> list[dict]:
        if on_conflict:
            conflict_keys = [key.strip() for key in on_conflict.split(",")]
            existing = [
                row
                for row in self.tables[path]
                if all(row.get(key) == payload.get(key) for key in conflict_keys)
            ]
            if existing:
                existing[0].update(payload)
                return [existing[0].copy()]
        return await self.insert(path, payload)

    async def patch(self, path: str, payload: dict, params: dict | None = None) -> list[dict]:
        rows = self.tables[path]
        matched_rows = rows
        if params:
            for key, value in params.items():
                if key in {"select", "order", "limit"}:
                    continue
                if isinstance(value, str) and value.startswith("eq."):
                    expected = value[3:]
                    matched_rows = [row for row in matched_rows if str(row.get(key)) == expected]
        for row in matched_rows:
            row.update(payload)
        return [row.copy() for row in matched_rows]


def run(coro):
    return asyncio.run(coro)


def test_meeting_agent_instructions_define_task_extraction_rules():
    from app.services import ai_meetings

    instructions = "\n".join(ai_meetings._meeting_agent_instructions())

    assert "Extract every explicit action item" in instructions
    assert "commitments, requests, follow-ups, blockers to resolve" in instructions
    assert "Do not skip a task only because the due date is missing" in instructions
    assert "Do not skip a task only because the assignee is unclear" in instructions
    assert "Infer priority even when the speaker does not explicitly say" in instructions


def test_calculate_task_priority_marks_urgent_keyword_even_without_assignee():
    from app.services import ai_meetings

    priority = ai_meetings._calculate_task_priority(
        ai_priority=None,
        due_date=None,
        reference_time="2026-05-29T10:00:00Z",
        evidence_segment={"text": "This is a blocker, someone needs to fix it."},
        title="Fix deployment issue",
        description=None,
    )

    assert priority == "urgent"


def test_calculate_task_priority_marks_today_text_as_urgent_without_due_date():
    from app.services import ai_meetings

    priority = ai_meetings._calculate_task_priority(
        ai_priority=None,
        due_date=None,
        reference_time="2026-05-29T10:00:00Z",
        evidence_segment={"text": "Please send the client report today."},
        title="Send client report",
        description=None,
    )

    assert priority == "urgent"


def test_calculate_task_priority_marks_due_today_as_urgent():
    from app.services import ai_meetings

    priority = ai_meetings._calculate_task_priority(
        ai_priority="low",
        due_date="2026-05-29",
        reference_time="2026-05-29T10:00:00Z",
        evidence_segment={"text": "Please send the report today."},
        title="Send report",
        description=None,
    )

    assert priority == "urgent"


def test_calculate_task_priority_marks_tomorrow_text_as_high_without_due_date():
    from app.services import ai_meetings

    priority = ai_meetings._calculate_task_priority(
        ai_priority=None,
        due_date=None,
        reference_time="2026-05-29T10:00:00Z",
        evidence_segment={"text": "Ravi will send the pricing notes tomorrow."},
        title="Send pricing notes",
        description=None,
    )

    assert priority == "high"


def test_calculate_task_priority_marks_due_within_two_days_as_high():
    from app.services import ai_meetings

    priority = ai_meetings._calculate_task_priority(
        ai_priority="medium",
        due_date="2026-05-31",
        reference_time="2026-05-29T10:00:00Z",
        evidence_segment={"text": "Ravi will send the pricing notes by Sunday."},
        title="Send pricing notes",
        description=None,
    )

    assert priority == "high"


def test_calculate_task_priority_marks_customer_work_as_high():
    from app.services import ai_meetings

    priority = ai_meetings._calculate_task_priority(
        ai_priority=None,
        due_date=None,
        reference_time="2026-05-29T10:00:00Z",
        evidence_segment={"text": "Priya will share the proposal with the customer."},
        title="Share proposal",
        description="Send the proposal to the customer.",
    )

    assert priority == "high"


def test_calculate_task_priority_marks_optional_work_as_low():
    from app.services import ai_meetings

    priority = ai_meetings._calculate_task_priority(
        ai_priority="medium",
        due_date=None,
        reference_time="2026-05-29T10:00:00Z",
        evidence_segment={"text": "If possible, update the notes later."},
        title="Update notes",
        description="Nice to have cleanup.",
    )

    assert priority == "low"


def test_calculate_task_priority_uses_ai_priority_as_fallback():
    from app.services import ai_meetings

    priority = ai_meetings._calculate_task_priority(
        ai_priority="high",
        due_date=None,
        reference_time="2026-05-29T10:00:00Z",
        evidence_segment={"text": "Ravi will prepare the internal summary."},
        title="Prepare internal summary",
        description=None,
    )

    assert priority == "high"


def test_generate_meeting_intelligence_creates_tasks_for_calendar_user(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "calendar-user-1",
            "subject": "Roadmap sync",
        }
    ]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "speaker": "Asha",
            "text": "Ravi will send the pricing notes tomorrow.",
            "created_at": "2026-05-20T10:00:00Z",
        }
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="The team agreed to send pricing notes.",
        key_points=["Pricing follow-up is needed."],
        decisions=["Send pricing notes to the client."],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send the pricing notes discussed in Roadmap sync.",
                priority="high",
                due_date=None,
                assignee_name=None,
                evidence_segment_sequence=None,
            )
        ],
    )
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["meeting_summaries"][0]["summary"] == ai_result.summary
    assert fake.tables["action_items"][0]["assignee_user_id"] is None
    assert fake.tables["tasks"][0]["owner_user_id"] == "calendar-user-1"
    assert fake.tables["tasks"][0]["assignee_user_id"] is None
    assert fake.tables["tasks"][0]["notification_status"] == "missing_recipient"
    assert fake.tables["tasks"][0]["meeting_id"] == "meeting-1"
    assert fake.tables["task_assignees"] == []


def test_generate_meeting_intelligence_infers_missing_assignee_from_evidence(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "calendar-user-1",
            "subject": "Roadmap sync",
        }
    ]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "text": "Ravi will send the pricing notes tomorrow.",
            "created_at": "2026-05-20T10:00:00Z",
        }
    ]
    fake.tables["meeting_participants"] = [
        {
            "meeting_id": "meeting-1",
            "source_id": "source-ravi",
            "display_name": "Ravi Sharma",
            "email": "ravi@example.com",
            "aad_user_id": "aad-ravi",
        }
    ]
    fake.tables["profiles"] = [
        {"id": "user-ravi", "display_name": "Ravi Sharma", "email": "ravi@example.com"}
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="Ravi owns the pricing follow-up.",
        key_points=["Pricing follow-up is needed."],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send the pricing notes discussed in Roadmap sync.",
                priority="high",
                due_date=None,
                assignee_name=None,
                evidence_segment_sequence=1,
            )
        ],
    )
    sent_emails = []

    def fake_send_task_email(**kwargs):
        sent_emails.append(kwargs)
        return ai_meetings.TaskEmailResult(sent=True, reason="sent")

    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)
    monkeypatch.setattr(ai_meetings, "send_task_assignment_email", fake_send_task_email)

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["action_items"][0]["assignee_user_id"] == "user-ravi"
    assert fake.tables["action_items"][0]["assignee_email"] == "ravi@example.com"
    assert fake.tables["action_items"][0]["assignee_resolution_status"] == "resolved"
    assert fake.tables["action_items"][0]["assignee_resolution_reason"] == (
        "evidence_text_participant_name"
    )
    assert fake.tables["tasks"][0]["assignee_user_id"] == "user-ravi"
    assert fake.tables["tasks"][0]["assignee_email"] == "ravi@example.com"
    assert fake.tables["task_assignees"] == [
        {
            "task_id": "tasks-1",
            "user_id": "user-ravi",
            "role": "primary",
            "created_at": fake.tables["task_assignees"][0]["created_at"],
        }
    ]
    assert sent_emails[0]["to_email"] == "ravi@example.com"


def test_generate_meeting_intelligence_normalizes_weekday_due_date(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "calendar-user-1",
            "subject": "Roadmap sync",
            "start_time": "2026-05-28T10:00:00Z",
        }
    ]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "text": "Ravi will send the pricing notes by Monday.",
            "created_at": "2026-05-28T10:00:00Z",
        }
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="The team agreed to send pricing notes.",
        key_points=["Pricing follow-up is needed."],
        decisions=["Send pricing notes to the client."],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send the pricing notes discussed in Roadmap sync.",
                priority="high",
                due_date="Monday",
                assignee_name=None,
                evidence_segment_sequence=1,
            )
        ],
    )
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["action_items"][0]["due_date"] == "2026-06-01"
    assert fake.tables["tasks"][0]["due_date"] == "2026-06-01"


def test_generate_meeting_intelligence_maps_monday_from_friday_reference(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "calendar-user-1",
            "subject": "Roadmap sync",
            "start_time": "2026-05-29T10:00:00Z",
        }
    ]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "text": "Ravi will send the pricing notes on Monday.",
            "created_at": "2026-05-29T10:00:00Z",
        }
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="The team agreed to send pricing notes.",
        key_points=["Pricing follow-up is needed."],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send the pricing notes discussed in Roadmap sync.",
                priority="high",
                due_date="Monday",
                assignee_name=None,
                evidence_segment_sequence=1,
            )
        ],
    )
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)

    run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert fake.tables["action_items"][0]["due_date"] == "2026-06-01"
    assert fake.tables["tasks"][0]["due_date"] == "2026-06-01"


def test_generate_meeting_intelligence_maps_prefixed_weekday_due_date(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "calendar-user-1",
            "subject": "Roadmap sync",
            "start_time": "2026-05-29T10:00:00Z",
        }
    ]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "text": "Ravi will send the pricing notes by Monday.",
            "created_at": "2026-05-29T10:00:00Z",
        }
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="The team agreed to send pricing notes.",
        key_points=["Pricing follow-up is needed."],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send the pricing notes discussed in Roadmap sync.",
                priority="high",
                due_date="by Monday",
                assignee_name=None,
                evidence_segment_sequence=1,
            )
        ],
    )
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)

    run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert fake.tables["action_items"][0]["due_date"] == "2026-06-01"
    assert fake.tables["tasks"][0]["due_date"] == "2026-06-01"


def test_generate_meeting_intelligence_corrects_stale_ai_due_date_year(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "calendar-user-1",
            "subject": "Roadmap sync",
            "start_time": "2026-05-29T10:00:00Z",
        }
    ]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "text": "Ravi will send the pricing notes on Monday.",
            "created_at": "2026-05-29T10:00:00Z",
        }
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="The team agreed to send pricing notes.",
        key_points=["Pricing follow-up is needed."],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send the pricing notes discussed in Roadmap sync.",
                priority="high",
                due_date="2024-06-01",
                assignee_name=None,
                evidence_segment_sequence=1,
            )
        ],
    )
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)

    run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert fake.tables["action_items"][0]["due_date"] == "2026-06-01"
    assert fake.tables["tasks"][0]["due_date"] == "2026-06-01"


def test_generate_meeting_intelligence_reports_duplicate_tasks(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "calendar-user-1",
            "subject": "Roadmap sync",
        }
    ]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "speaker": "Asha",
            "text": "Ravi will send the pricing notes tomorrow.",
            "created_at": "2026-05-20T10:00:00Z",
        }
    ]
    fake.tables["action_items"] = [
        {
            "id": "action_items-1",
            "meeting_id": "meeting-1",
            "assignee_user_id": "calendar-user-1",
            "title": "Send pricing notes",
            "description": "Send the pricing notes discussed in Roadmap sync.",
            "priority": "high",
            "due_date": None,
        }
    ]
    fake.tables["tasks"] = [
        {
            "id": "tasks-1",
            "owner_user_id": "calendar-user-1",
            "assignee_user_id": "calendar-user-1",
            "meeting_id": "meeting-1",
            "action_item_id": "action_items-1",
            "title": "Send pricing notes",
            "description": "Send the pricing notes discussed in Roadmap sync.",
            "status": "todo",
            "priority": "high",
            "due_date": None,
        }
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="The team agreed to send pricing notes.",
        key_points=["Pricing follow-up is needed."],
        decisions=["Send pricing notes to the client."],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send the pricing notes discussed in Roadmap sync.",
                priority="high",
                due_date=None,
                assignee_name="Ravi",
                evidence_segment_sequence=1,
            )
        ],
    )
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_action_items_count"] == 0
    assert result["skipped_action_items_count"] == 1
    assert result["created_tasks_count"] == 0
    assert result["skipped_tasks_count"] == 1
    assert len(fake.tables["action_items"]) == 1
    assert len(fake.tables["tasks"]) == 1


def test_uploaded_recording_tasks_do_not_send_email(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "calendar-user-1",
            "subject": "Uploaded sync",
            "source_type": "uploaded_recording",
        }
    ]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "text": "Ravi will send the pricing notes tomorrow.",
            "created_at": "2026-05-20T10:00:00Z",
        }
    ]
    fake.tables["meeting_participants"] = [
        {
            "meeting_id": "meeting-1",
            "source_id": "source-ravi",
            "display_name": "Ravi Sharma",
            "email": "ravi@example.com",
            "aad_user_id": "aad-ravi",
        }
    ]
    fake.tables["profiles"] = [
        {"id": "user-ravi", "display_name": "Ravi Sharma", "email": "ravi@example.com"}
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="Ravi owns the pricing follow-up.",
        key_points=[],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send pricing notes to the client.",
                priority="high",
                due_date=None,
                assignee_name="Ravi",
                evidence_segment_sequence=1,
            )
        ],
    )
    sent_emails = []

    def fake_send_task_email(**kwargs):
        sent_emails.append(kwargs)
        return ai_meetings.TaskEmailResult(sent=True, reason="sent")

    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)
    monkeypatch.setattr(ai_meetings, "send_task_assignment_email", fake_send_task_email)

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["tasks"][0]["notification_status"] == "not_required"
    assert sent_emails == []


def test_generate_meeting_intelligence_enriches_existing_action_item_email_and_sends(
    monkeypatch,
):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "calendar-user-1",
            "subject": "Roadmap sync",
        }
    ]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "text": "Ravi will send the pricing notes tomorrow.",
            "created_at": "2026-05-20T10:00:00Z",
        }
    ]
    fake.tables["meeting_participants"] = [
        {
            "meeting_id": "meeting-1",
            "source_id": "source-ravi",
            "display_name": "Ravi Sharma",
            "email": "ravi@example.com",
            "aad_user_id": "aad-ravi",
        }
    ]
    fake.tables["action_items"] = [
        {
            "id": "action_items-1",
            "meeting_id": "meeting-1",
            "assignee_user_id": None,
            "assignee_display_name": "Ravi Sharma",
            "assignee_email": None,
            "title": "Send pricing notes",
            "description": "Send the pricing notes discussed in Roadmap sync.",
            "priority": "high",
            "due_date": None,
        }
    ]
    fake.tables["tasks"] = [
        {
            "id": "tasks-1",
            "owner_user_id": "calendar-user-1",
            "assignee_user_id": None,
            "assignee_email": None,
            "notification_status": "not_sent",
            "meeting_id": "meeting-1",
            "action_item_id": "action_items-1",
            "title": "Send pricing notes",
            "description": "Send the pricing notes discussed in Roadmap sync.",
            "status": "todo",
            "priority": "high",
            "due_date": None,
        }
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="Ravi owns pricing follow-up.",
        key_points=[],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send pricing notes to the client.",
                priority="high",
                due_date=None,
                assignee_name=None,
                evidence_segment_sequence=1,
            )
        ],
    )
    sent = []
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)
    monkeypatch.setattr(
        ai_meetings,
        "send_task_assignment_email",
        lambda **kwargs: sent.append(kwargs) or ai_meetings.TaskEmailResult(True, "sent"),
    )

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_action_items_count"] == 0
    assert result["skipped_action_items_count"] == 1
    assert result["created_tasks_count"] == 0
    assert result["skipped_tasks_count"] == 1
    assert fake.tables["action_items"][0]["assignee_email"] == "ravi@example.com"
    assert fake.tables["tasks"][0]["assignee_email"] == "ravi@example.com"
    assert fake.tables["tasks"][0]["notification_status"] == "sent"
    assert sent[0]["to_email"] == "ravi@example.com"
    assert sent[0]["assignee_name"] == "Ravi Sharma"


def test_generate_meeting_intelligence_assigns_named_user_and_sends_email(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [{"id": "meeting-1", "user_id": "owner-1", "subject": "Roadmap sync"}]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "source_id": "source-asha",
            "text": "Ravi will send the pricing notes tomorrow.",
            "created_at": "2026-05-20T10:00:00Z",
        }
    ]
    fake.tables["meeting_participants"] = [
        {
            "meeting_id": "meeting-1",
            "source_id": "source-ravi",
            "display_name": "Ravi Sharma",
            "email": "ravi@example.com",
            "aad_user_id": "aad-ravi",
        }
    ]
    fake.tables["profiles"] = [
        {"id": "user-ravi", "display_name": "Ravi Sharma", "email": "ravi@example.com"}
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="Ravi owns pricing follow-up.",
        key_points=[],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send pricing notes to the client.",
                priority="high",
                due_date=None,
                assignee_name="Ravi",
                evidence_segment_sequence=1,
            )
        ],
    )
    sent = []
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)
    monkeypatch.setattr(
        ai_meetings,
        "send_task_assignment_email",
        lambda **kwargs: sent.append(kwargs) or ai_meetings.TaskEmailResult(True, "sent"),
    )

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["tasks"][0]["assignee_user_id"] == "user-ravi"
    assert fake.tables["tasks"][0]["assignee_email"] == "ravi@example.com"
    assert fake.tables["task_assignees"][0]["user_id"] == "user-ravi"
    assert fake.tables["tasks"][0]["notification_status"] == "sent"
    assert sent[0]["to_email"] == "ravi@example.com"


def test_generate_meeting_intelligence_sends_email_to_resolved_participant_without_profile(
    monkeypatch,
):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [{"id": "meeting-1", "user_id": "owner-1", "subject": "Roadmap sync"}]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "source_id": "source-asha",
            "text": "Ravi will send the pricing notes tomorrow.",
            "created_at": "2026-05-20T10:00:00Z",
        }
    ]
    fake.tables["meeting_participants"] = [
        {
            "meeting_id": "meeting-1",
            "source_id": "source-ravi",
            "display_name": "Ravi Sharma",
            "email": "ravi@example.com",
            "aad_user_id": "aad-ravi",
        }
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="Ravi owns pricing follow-up.",
        key_points=[],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send pricing notes to the client.",
                priority="high",
                due_date=None,
                assignee_name="Ravi",
                evidence_segment_sequence=1,
            )
        ],
    )
    sent = []
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)
    monkeypatch.setattr(
        ai_meetings,
        "send_task_assignment_email",
        lambda **kwargs: sent.append(kwargs) or ai_meetings.TaskEmailResult(True, "sent"),
    )

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["tasks"][0]["assignee_user_id"] is None
    assert fake.tables["tasks"][0]["assignee_email"] == "ravi@example.com"
    assert fake.tables["task_assignees"] == []
    assert fake.tables["tasks"][0]["notification_status"] == "sent"
    assert sent[0]["to_email"] == "ravi@example.com"
    assert sent[0]["assignee_name"] == "Ravi Sharma"


def test_generate_meeting_intelligence_skips_email_when_assignee_ambiguous(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [{"id": "meeting-1", "user_id": "owner-1", "subject": "Roadmap sync"}]
    fake.tables["transcript_segments"] = [
        {"id": "segment-1", "sequence": 1, "speaker": "Asha", "text": "Ravi will send it."}
    ]
    fake.tables["meeting_participants"] = [
        {"display_name": "Ravi Sharma", "email": "ravi@example.com"},
        {"display_name": "Ravi Kumar", "email": "ravi.kumar@example.com"},
    ]
    fake.tables["profiles"] = [
        {"id": "user-1", "display_name": "Ravi Sharma", "email": "ravi@example.com"},
        {"id": "user-2", "display_name": "Ravi Kumar", "email": "ravi.kumar@example.com"},
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="Follow-up needed.",
        key_points=[],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send follow-up",
                assignee_name="Ravi",
                evidence_segment_sequence=1,
            )
        ],
    )
    sent = []
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)
    monkeypatch.setattr(
        ai_meetings,
        "send_task_assignment_email",
        lambda **kwargs: sent.append(kwargs),
    )

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["tasks"][0]["assignee_user_id"] is None
    assert fake.tables["tasks"][0]["notification_status"] == "not_sent"
    assert sent == []


def test_generate_meeting_intelligence_does_not_assign_first_person_without_evidence(
    monkeypatch,
):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [{"id": "meeting-1", "user_id": "owner-1", "subject": "Roadmap sync"}]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Ravi Sharma",
            "source_id": "source-ravi",
            "speaker_email": "ravi@example.com",
            "text": "I will send the pricing notes tomorrow.",
        }
    ]
    fake.tables["meeting_participants"] = [
        {
            "meeting_id": "meeting-1",
            "source_id": "source-ravi",
            "display_name": "Ravi Sharma",
            "email": "ravi@example.com",
        }
    ]
    fake.tables["profiles"] = [
        {"id": "user-ravi", "display_name": "Ravi Sharma", "email": "ravi@example.com"}
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="Ravi owns pricing follow-up.",
        key_points=[],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                assignee_name="I",
                evidence_segment_sequence=None,
            )
        ],
    )
    sent = []
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)
    monkeypatch.setattr(
        ai_meetings,
        "send_task_assignment_email",
        lambda **kwargs: sent.append(kwargs) or ai_meetings.TaskEmailResult(True, "sent"),
    )

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["action_items"][0]["assignee_resolution_status"] == "unresolved"
    assert fake.tables["tasks"][0]["assignee_user_id"] is None
    assert fake.tables["tasks"][0]["notification_status"] == "not_sent"
    assert sent == []


def test_parse_ai_result_rejects_non_json_response():
    from app.services import ai_meetings

    with pytest.raises(HTTPException) as exc:
        ai_meetings._parse_ai_result("None")

    assert exc.value.status_code == 502
    assert "valid JSON" in exc.value.detail
