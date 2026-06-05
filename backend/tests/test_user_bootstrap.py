import asyncio


class FakeSupabaseGateway:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, dict, str | None]] = []
        self.patches: list[tuple[str, dict, dict]] = []
        self.tables: dict[str, list[dict]] = {
            "profiles": [],
            "calendar_connections": [],
            "meeting_settings": [],
        }

    async def upsert(
        self,
        path: str,
        payload: dict,
        on_conflict: str | None = None,
    ) -> list[dict]:
        self.upserts.append((path, payload.copy(), on_conflict))
        return [payload.copy()]

    async def get(self, path: str, params: dict | None = None) -> list[dict]:
        rows = list(self.tables.get(path, []))
        if params and "id" in params:
            expected = params["id"].removeprefix("eq.")
            rows = [row for row in rows if row.get("id") == expected]
        if params and "user_id" in params:
            expected = params["user_id"].removeprefix("eq.")
            rows = [row for row in rows if row.get("user_id") == expected]
        if params and "provider" in params:
            expected = params["provider"].removeprefix("eq.")
            rows = [row for row in rows if row.get("provider") == expected]
        if params and "limit" in params:
            rows = rows[: int(params["limit"])]
        return [row.copy() for row in rows]

    async def patch(self, path: str, payload: dict, params: dict) -> list[dict]:
        self.patches.append((path, payload.copy(), params.copy()))
        rows = self.tables.get(path, [])
        updated: list[dict] = []
        for row in rows:
            if params.get("id") == f"eq.{row.get('id')}":
                row.update(payload)
                updated.append(row.copy())
        return updated


def run(coro):
    return asyncio.run(coro)


def test_ensure_user_workspace_upserts_profile_calendar_connection_and_settings(monkeypatch):
    from app.services import user_bootstrap

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(user_bootstrap, "supabase_gateway", fake)

    result = run(
        user_bootstrap.ensure_user_workspace(
            user_id="auth-user-id",
            email="person@example.com",
            tenant_id="tenant-1",
            aad_user_id="aad-user-1",
        )
    )

    assert result == {
        "user_id": "auth-user-id",
        "calendar_connection_status": "connected",
    }
    assert fake.upserts == [
        (
            "profiles",
            {
                "id": "auth-user-id",
                "email": "person@example.com",
            },
            "id",
        ),
        (
            "meeting_settings",
            {
                "user_id": "auth-user-id",
                "auto_join_enabled": False,
                "require_approval": True,
                "approval_lead_minutes": 2,
                "look_ahead_minutes": 15,
                "join_early_seconds": 0,
                "max_late_join_minutes": 10,
                "leave_grace_minutes": 2,
                "use_service_hosted_media": False,
            },
            "user_id",
        ),
        (
            "calendar_connections",
            {
                "user_id": "auth-user-id",
                "provider": "microsoft",
                "tenant_id": "tenant-1",
                "aad_user_id": "aad-user-1",
                "email": "person@example.com",
                "enabled": True,
                "connection_status": "connected",
            },
            "user_id,provider",
        ),
    ]


def test_ensure_user_workspace_keeps_calendar_pending_without_email(monkeypatch):
    from app.services import user_bootstrap

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(user_bootstrap, "supabase_gateway", fake)

    result = run(user_bootstrap.ensure_user_workspace(user_id="auth-user-id", email=None))

    assert result == {
        "user_id": "auth-user-id",
        "calendar_connection_status": "pending",
    }
    calendar_payload = fake.upserts[2][1]
    assert calendar_payload["email"] == "auth-user-id"
    assert calendar_payload["enabled"] is False
    assert calendar_payload["connection_status"] == "pending"


def test_get_onboarding_status_returns_false_without_profile(monkeypatch):
    from app.services import user_bootstrap

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(user_bootstrap, "supabase_gateway", fake)

    result = run(user_bootstrap.get_onboarding_status("auth-user-id"))

    assert result == {
        "user_id": "auth-user-id",
        "onboarding_completed": False,
        "onboarding_completed_at": None,
        "calendar_connection_status": None,
        "auto_join_enabled": False,
    }


def test_get_onboarding_status_reads_profile_calendar_and_settings(monkeypatch):
    from app.services import user_bootstrap

    fake = FakeSupabaseGateway()
    fake.tables["profiles"] = [
        {
            "id": "auth-user-id",
            "onboarding_completed_at": "2026-06-05T10:00:00Z",
        }
    ]
    fake.tables["calendar_connections"] = [
        {
            "user_id": "auth-user-id",
            "provider": "microsoft",
            "connection_status": "connected",
        }
    ]
    fake.tables["meeting_settings"] = [
        {
            "user_id": "auth-user-id",
            "auto_join_enabled": True,
        }
    ]
    monkeypatch.setattr(user_bootstrap, "supabase_gateway", fake)

    result = run(user_bootstrap.get_onboarding_status("auth-user-id"))

    assert result == {
        "user_id": "auth-user-id",
        "onboarding_completed": True,
        "onboarding_completed_at": "2026-06-05T10:00:00Z",
        "calendar_connection_status": "connected",
        "auto_join_enabled": True,
    }


def test_complete_onboarding_marks_profile_completed(monkeypatch):
    from app.services import user_bootstrap

    fake = FakeSupabaseGateway()
    fake.tables["profiles"] = [{"id": "auth-user-id", "email": "person@example.com"}]
    monkeypatch.setattr(user_bootstrap, "supabase_gateway", fake)

    result = run(user_bootstrap.complete_onboarding("auth-user-id"))

    assert result["onboarding_completed"] is True
    assert result["onboarding_completed_at"]
    assert fake.patches[0][0] == "profiles"
    assert fake.patches[0][1]["onboarding_completed_at"]
    assert fake.patches[0][2] == {"id": "eq.auth-user-id"}
