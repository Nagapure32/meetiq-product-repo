import asyncio


class FakeSupabaseGateway:
    def __init__(self) -> None:
        self.get_calls: list[tuple[str, dict | None]] = []
        self.tables: dict[str, list[dict]] = {
            "meetings": [
                {
                    "id": "meeting-with-transcript",
                    "user_id": "user-1",
                    "subject": "Captured meeting",
                    "start_time": "2026-05-20T10:00:00Z",
                    "end_time": "2026-05-20T10:30:00Z",
                    "status": "completed",
                    "bot_status": "completed",
                    "approval_status": "approved",
                },
                {
                    "id": "meeting-rejected",
                    "user_id": "user-1",
                    "subject": "Rejected meeting",
                    "start_time": "2026-05-20T11:00:00Z",
                    "end_time": "2026-05-20T11:30:00Z",
                    "status": "completed",
                    "bot_status": "not_started",
                    "approval_status": "rejected",
                },
                {
                    "id": "meeting-expired",
                    "user_id": "user-1",
                    "subject": "Expired meeting",
                    "start_time": "2026-05-20T12:00:00Z",
                    "end_time": "2026-05-20T12:30:00Z",
                    "status": "completed",
                    "bot_status": "not_started",
                    "approval_status": "expired",
                },
            ],
            "transcript_segments": [
                {"id": "segment-1", "meeting_id": "meeting-with-transcript"},
                {"id": "segment-2", "meeting_id": "meeting-with-transcript"},
            ],
        }

    async def get(self, path: str, params: dict | None = None) -> list[dict]:
        self.get_calls.append((path, params))
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
                expected = value[4:-1].split(",")
                rows = [row for row in rows if str(row.get(key)) in expected]

        if params.get("limit"):
            rows = rows[: int(params["limit"])]
        return rows


def run(coro):
    return asyncio.run(coro)


def test_list_user_meetings_adds_transcript_segment_counts(monkeypatch):
    from app.services import meetings

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(meetings, "supabase_gateway", fake)
    monkeypatch.setattr(meetings, "get_dev_user_id", lambda: "user-1")

    result = run(meetings.list_user_meetings())

    counts = {meeting["id"]: meeting["transcript_segment_count"] for meeting in result}
    assert counts == {
        "meeting-with-transcript": 2,
        "meeting-rejected": 0,
        "meeting-expired": 0,
    }


def test_list_user_meetings_can_filter_to_transcript_ready(monkeypatch):
    from app.services import meetings

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(meetings, "supabase_gateway", fake)
    monkeypatch.setattr(meetings, "get_dev_user_id", lambda: "user-1")

    result = run(meetings.list_user_meetings(transcript_ready=True))

    assert [meeting["id"] for meeting in result] == ["meeting-with-transcript"]
    assert result[0]["transcript_segment_count"] == 2


def test_list_meeting_transcript_orders_by_sequence_then_timestamps(monkeypatch):
    from app.services import meetings

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(meetings, "supabase_gateway", fake)

    run(meetings.list_meeting_transcript("meeting-with-transcript", user_id="user-1"))

    path, params = fake.get_calls[-1]
    assert path == "transcript_segments"
    assert params is not None
    assert params["order"] == "sequence.asc.nullslast,started_at.asc.nullslast,created_at.asc"
