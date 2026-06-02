import asyncio
from datetime import UTC, datetime


class FakeSupabaseGateway:
    def __init__(self):
        self.tables = {"transcript_segments": [], "meeting_participants": []}

    async def insert(self, path, payload):
        rows = payload if isinstance(payload, list) else [payload]
        self.tables[path].extend(rows)
        return rows

    async def upsert(self, path, payload, on_conflict=None):
        if on_conflict:
            conflict_keys = [key.strip() for key in on_conflict.split(",")]
            for row in self.tables[path]:
                if all(row.get(key) == payload.get(key) for key in conflict_keys):
                    row.update(payload)
                    return [row]
        self.tables[path].append(payload)
        return [payload]


def run(coro):
    return asyncio.run(coro)


def test_record_bot_transcript_stores_speaker_identity(monkeypatch):
    from app.internal.schemas import BotTranscriptRequest, BotTranscriptSegment
    from app.services import bot_reporting

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(bot_reporting, "supabase_gateway", fake)

    run(
        bot_reporting.record_bot_transcript(
            BotTranscriptRequest(
                meeting_id="meeting-1",
                segments=[
                    BotTranscriptSegment(
                        sequence=1,
                        speaker="Ravi Sharma",
                        source_id="7",
                        speaker_participant_id="participant-1",
                        speaker_aad_user_id="aad-ravi",
                        speaker_email="ravi@example.com",
                        speaker_user_principal_name="ravi@example.com",
                        text="I will send the notes.",
                        started_at=datetime.now(UTC),
                        ended_at=datetime.now(UTC),
                    )
                ],
            )
        )
    )

    assert fake.tables["transcript_segments"][0]["speaker_aad_user_id"] == "aad-ravi"
    assert fake.tables["meeting_participants"][0]["email"] == "ravi@example.com"


def test_record_bot_transcript_preserves_existing_participant_email(monkeypatch):
    from app.internal.schemas import BotTranscriptRequest, BotTranscriptSegment
    from app.services import bot_reporting

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(bot_reporting, "supabase_gateway", fake)

    run(
        bot_reporting.record_bot_transcript(
            BotTranscriptRequest(
                meeting_id="meeting-1",
                segments=[
                    BotTranscriptSegment(
                        sequence=1,
                        speaker="Ravi Sharma",
                        source_id="7",
                        speaker_email="ravi@example.com",
                        text="I will send the notes.",
                    )
                ],
            )
        )
    )
    run(
        bot_reporting.record_bot_transcript(
            BotTranscriptRequest(
                meeting_id="meeting-1",
                segments=[
                    BotTranscriptSegment(
                        sequence=2,
                        speaker="Ravi Sharma",
                        source_id="7",
                        speaker_email=None,
                        text="Following up now.",
                    )
                ],
            )
        )
    )

    assert len(fake.tables["meeting_participants"]) == 1
    assert fake.tables["meeting_participants"][0]["email"] == "ravi@example.com"
