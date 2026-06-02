import asyncio


class FakeSupabaseGateway:
    async def get(self, path: str, params: dict | None = None) -> list[dict]:
        assert path == "bot_calendar_users"
        assert params == {"select": "*"}
        return [
            {
                "user_id": "auth-user-id",
                "tenant_id": "tenant-1",
                "aad_user_id": "aad-user-1",
                "email": "person@example.com",
                "auto_join_enabled": True,
                "require_approval": False,
                "look_ahead_minutes": 30,
                "approval_lead_minutes": 5,
                "join_early_seconds": 10,
                "max_late_join_minutes": 20,
                "leave_grace_minutes": 3,
            }
        ]


def run(coro):
    return asyncio.run(coro)


def test_list_enabled_calendar_users_returns_bot_contract(monkeypatch):
    from app.services import bot_calendar_users

    monkeypatch.setattr(bot_calendar_users, "supabase_gateway", FakeSupabaseGateway())

    result = run(bot_calendar_users.list_enabled_calendar_users())

    assert [user.model_dump() for user in result] == [
        {
            "user_id": "auth-user-id",
            "tenant_id": "tenant-1",
            "aad_user_id": "aad-user-1",
            "email": "person@example.com",
            "auto_join_enabled": True,
            "require_approval": False,
            "look_ahead_minutes": 30,
            "approval_lead_minutes": 5,
            "join_early_seconds": 10,
            "max_late_join_minutes": 20,
            "leave_grace_minutes": 3,
        }
    ]

