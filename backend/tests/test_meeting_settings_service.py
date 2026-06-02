import asyncio


class FakeSupabaseGateway:
    def __init__(self) -> None:
        self.tables = {
            "meeting_settings": [
                {
                    "user_id": "auth-user-id",
                    "auto_join_enabled": True,
                    "require_approval": False,
                    "approval_lead_minutes": 5,
                    "look_ahead_minutes": 30,
                    "join_early_seconds": 10,
                    "max_late_join_minutes": 20,
                    "leave_grace_minutes": 3,
                    "use_service_hosted_media": True,
                }
            ]
        }
        self.upserts: list[dict] = []

    async def get(self, path: str, params: dict | None = None) -> list[dict]:
        rows = [row.copy() for row in self.tables[path]]
        if params and "user_id" in params:
            expected = params["user_id"].removeprefix("eq.")
            rows = [row for row in rows if row.get("user_id") == expected]
        return rows[: int(params.get("limit", len(rows)))] if params else rows

    async def upsert(
        self,
        path: str,
        payload: dict,
        on_conflict: str | None = None,
    ) -> list[dict]:
        self.upserts.append(payload.copy())
        return [payload.copy()]


def run(coro):
    return asyncio.run(coro)


def test_get_meeting_assistant_settings_uses_explicit_user_id(monkeypatch):
    from app.services import meeting_settings

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(meeting_settings, "supabase_gateway", fake)

    result = run(meeting_settings.get_meeting_assistant_settings("auth-user-id"))

    assert result.user_id == "auth-user-id"
    assert result.auto_join_enabled is True
    assert result.require_approval is False


def test_update_meeting_assistant_settings_uses_explicit_user_id(monkeypatch):
    from app.api.v1.schemas import MeetingAssistantSettings
    from app.services import meeting_settings

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(meeting_settings, "supabase_gateway", fake)

    result = run(
        meeting_settings.update_meeting_assistant_settings(
            MeetingAssistantSettings(auto_join_enabled=True),
            "auth-user-id",
        )
    )

    assert result.user_id == "auth-user-id"
    assert fake.upserts[0]["user_id"] == "auth-user-id"
    assert fake.upserts[0]["auto_join_enabled"] is True

