import asyncio

import pytest
from fastapi import HTTPException


class FakeSupabaseGateway:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {
            "meetings": [
                {
                    "id": "meeting-1",
                    "user_id": "user-1",
                    "subject": "Sprint planning",
                    "join_url": "https://teams.microsoft.com/l/meetup-join/abc",
                    "bot_status": "not_started",
                    "status": "detected",
                }
            ]
        }
        self.patches: list[tuple[str, dict, dict]] = []

    async def get(self, path: str, params: dict | None = None) -> list[dict]:
        rows = [row.copy() for row in self.tables[path]]
        if not params:
            return rows

        for key, value in params.items():
            if key in {"select", "limit"}:
                continue
            if isinstance(value, str) and value.startswith("eq."):
                expected = value[3:]
                rows = [row for row in rows if str(row.get(key)) == expected]
        return rows

    async def patch(self, path: str, payload: dict, params: dict) -> list[dict]:
        self.patches.append((path, payload, params))
        rows = await self.get(path, params)
        ids = {row["id"] for row in rows}
        patched = []
        for row in self.tables[path]:
            if row.get("id") in ids:
                row.update(payload)
                patched.append(row.copy())
        return patched


def run(coro):
    return asyncio.run(coro)


def test_manual_join_existing_meeting_calls_dotnet_bot(monkeypatch):
    from app.api.v1.schemas import ManualJoinRequest
    from app.services import bot_manual_join

    fake = FakeSupabaseGateway()
    calls = []

    async def fake_call(payload: dict) -> dict:
        calls.append(payload)
        return {
            "callId": "call-1",
            "state": "establishing",
            "joinMode": "joinWebUrl",
            "mediaMode": "app-hosted",
            "message": "Call creation was accepted by Graph.",
        }

    monkeypatch.setattr(bot_manual_join, "supabase_gateway", fake)
    monkeypatch.setattr(bot_manual_join.settings, "teams_bot_base_url", "http://bot.local")
    monkeypatch.setattr(bot_manual_join, "_call_bot_join_endpoint", fake_call)

    result = run(
        bot_manual_join.manual_join_meeting(
            ManualJoinRequest(meeting_id="meeting-1", use_service_hosted_media=False)
        )
    )

    assert calls == [
        {
            "joinWebUrl": "https://teams.microsoft.com/l/meetup-join/abc",
            "useServiceHostedMedia": False,
        }
    ]
    assert result["meeting_id"] == "meeting-1"
    assert result["call_id"] == "call-1"
    assert fake.tables["meetings"][0]["bot_status"] == "joining"


def test_manual_join_extracts_meeting_id_and_passcode_from_join_url(monkeypatch):
    from app.api.v1.schemas import ManualJoinRequest
    from app.services import bot_manual_join

    calls = []

    async def fake_call(payload: dict) -> dict:
        calls.append(payload)
        return {"message": "accepted"}

    monkeypatch.setattr(bot_manual_join.settings, "teams_bot_base_url", "http://bot.local")
    monkeypatch.setattr(bot_manual_join, "_call_bot_join_endpoint", fake_call)

    run(
        bot_manual_join.manual_join_meeting(
            ManualJoinRequest(
                join_web_url=(
                    "https://teams.microsoft.com/l/meetup-join/abc"
                    "?meetingId=123%20456%20789&passcode=A1b2C3"
                ),
                use_service_hosted_media=False,
            )
        )
    )

    assert calls == [
        {
            "joinWebUrl": (
                "https://teams.microsoft.com/l/meetup-join/abc"
                "?meetingId=123%20456%20789&passcode=A1b2C3"
            ),
            "joinMeetingId": "123 456 789",
            "passcode": "A1b2C3",
            "useServiceHostedMedia": False,
        }
    ]


def test_manual_join_uses_extracted_id_passcode_when_invite_text_has_no_url(monkeypatch):
    from app.api.v1.schemas import ManualJoinRequest
    from app.services import bot_manual_join

    calls = []

    async def fake_call(payload: dict) -> dict:
        calls.append(payload)
        return {"message": "accepted"}

    monkeypatch.setattr(bot_manual_join.settings, "teams_bot_base_url", "http://bot.local")
    monkeypatch.setattr(bot_manual_join, "_call_bot_join_endpoint", fake_call)

    run(
        bot_manual_join.manual_join_meeting(
            ManualJoinRequest(
                join_web_url="Microsoft Teams Meeting\nMeeting ID: 123 456 789\nPasscode: A1b2C3",
                use_service_hosted_media=False,
            )
        )
    )

    assert calls == [
        {
            "joinMeetingId": "123 456 789",
            "passcode": "A1b2C3",
            "useServiceHostedMedia": False,
        }
    ]


def test_manual_join_requires_join_details():
    from app.api.v1.schemas import ManualJoinRequest
    from app.services import bot_manual_join

    with pytest.raises(HTTPException) as exc:
        run(bot_manual_join.manual_join_meeting(ManualJoinRequest()))

    assert exc.value.status_code == 422
    assert "meeting or Teams join details" in exc.value.detail
