import asyncio
from datetime import UTC, datetime

from app.internal.schemas import BotMeetingUpsertRequest, BotTranscriptRequest


class FakeSupabaseGateway:
    def __init__(self) -> None:
        self.insert_calls: list[tuple[str, dict | list[dict]]] = []
        self.tables: dict[str, list[dict]] = {
            "meeting_instances": [],
            "meeting_user_intents": [],
            "meeting_participants": [],
            "meetings": [],
        }

    async def insert(self, path: str, payload: dict | list[dict]) -> list[dict]:
        self.insert_calls.append((path, payload))
        rows = payload if isinstance(payload, list) else [payload]
        return [row.copy() for row in rows]

    async def upsert(
        self,
        path: str,
        payload: dict,
        on_conflict: str | None = None,
    ) -> list[dict]:
        if on_conflict:
            conflict_keys = [key.strip() for key in on_conflict.split(",")]
            for row in self.tables[path]:
                if all(row.get(key) == payload.get(key) for key in conflict_keys):
                    row.update(payload)
                    return [row.copy()]

        row = payload.copy()
        row.setdefault("id", f"{path}-{len(self.tables[path]) + 1}")
        self.tables[path].append(row)
        return [row.copy()]


def run(coro):
    return asyncio.run(coro)


def test_record_bot_transcript_preserves_sequence(monkeypatch):
    from app.services import bot_reporting

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(bot_reporting, "supabase_gateway", fake)

    payload = BotTranscriptRequest.model_validate(
        {
            "meeting_id": "meeting-1",
            "segments": [
                {
                    "sequence": 42,
                    "speaker": "Asha",
                    "source_id": "speaker-1",
                    "language": "en-US",
                    "text": "We should ship this in order.",
                    "started_at": datetime(2026, 5, 25, 10, 30, tzinfo=UTC),
                    "ended_at": datetime(2026, 5, 25, 10, 30, tzinfo=UTC),
                }
            ],
        }
    )

    run(bot_reporting.record_bot_transcript(payload))

    path, rows = fake.insert_calls[0]
    assert path == "transcript_segments"
    assert isinstance(rows, list)
    assert rows[0]["sequence"] == 42


def test_bot_meeting_upsert_schema_accepts_dedupe_metadata():
    payload = BotMeetingUpsertRequest.model_validate(
        {
            "user_id": "user-1",
            "graph_event_id": "event-1",
            "dedupe_key": "teams:abc",
            "calendar_user_email": "ravi@example.com",
            "subject": "Planning",
            "join_url": "https://teams.microsoft.com/l/meetup-join/abc",
            "start_time": datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            "end_time": datetime(2026, 5, 28, 10, 30, tzinfo=UTC),
        }
    )

    assert payload.dedupe_key == "teams:abc"
    assert payload.calendar_user_email == "ravi@example.com"


def test_upsert_bot_meeting_creates_shared_instance_and_user_intent(monkeypatch):
    from app.services import bot_reporting

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(bot_reporting, "supabase_gateway", fake)
    payload = BotMeetingUpsertRequest.model_validate(
        {
            "user_id": "user-1",
            "graph_event_id": "event-1",
            "dedupe_key": "teams:abc",
            "calendar_user_email": "ravi@example.com",
            "subject": "Planning",
            "join_url": "https://teams.microsoft.com/l/meetup-join/abc",
            "start_time": datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            "end_time": datetime(2026, 5, 28, 10, 30, tzinfo=UTC),
            "approval_status": "Pending",
        }
    )

    meeting = run(bot_reporting.upsert_bot_meeting(payload))

    assert meeting["id"] == "meetings-1"
    assert len(fake.tables["meetings"]) == 1
    assert fake.tables["meeting_instances"] == [
        {
            "id": "meeting_instances-1",
            "dedupe_key": "teams:abc",
            "join_url": "https://teams.microsoft.com/l/meetup-join/abc",
            "subject": "Planning",
            "organizer_email": None,
            "start_time": "2026-05-28T10:00:00+00:00",
            "end_time": "2026-05-28T10:30:00+00:00",
            "bot_status": "not_started",
            "updated_at": fake.tables["meeting_instances"][0]["updated_at"],
        }
    ]
    assert fake.tables["meeting_user_intents"] == [
        {
            "id": "meeting_user_intents-1",
            "meeting_instance_id": "meeting_instances-1",
            "user_id": "user-1",
            "meeting_id": "meetings-1",
            "graph_event_id": "event-1",
            "calendar_email": "ravi@example.com",
            "approval_status": "Pending",
            "updated_at": fake.tables["meeting_user_intents"][0]["updated_at"],
        }
    ]


def test_upsert_bot_meeting_reuses_shared_instance_for_duplicate_meeting(monkeypatch):
    from app.services import bot_reporting

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(bot_reporting, "supabase_gateway", fake)

    for user_id, event_id, email in [
        ("user-1", "event-1", "ravi@example.com"),
        ("user-2", "event-2", "asha@example.com"),
    ]:
        payload = BotMeetingUpsertRequest.model_validate(
            {
                "user_id": user_id,
                "graph_event_id": event_id,
                "dedupe_key": "teams:abc",
                "calendar_user_email": email,
                "subject": "Planning",
                "join_url": "https://teams.microsoft.com/l/meetup-join/abc",
                "start_time": datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
                "end_time": datetime(2026, 5, 28, 10, 30, tzinfo=UTC),
                "approval_status": "Pending",
            }
        )
        run(bot_reporting.upsert_bot_meeting(payload))

    assert len(fake.tables["meetings"]) == 2
    assert len(fake.tables["meeting_instances"]) == 1
    assert len(fake.tables["meeting_user_intents"]) == 2
    assert {
        row["user_id"]: row["meeting_instance_id"]
        for row in fake.tables["meeting_user_intents"]
    } == {
        "user-1": "meeting_instances-1",
        "user-2": "meeting_instances-1",
    }
