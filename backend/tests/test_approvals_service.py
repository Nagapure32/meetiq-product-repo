import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException


class FakeSupabaseGateway:
    def __init__(self) -> None:
        now = datetime.now(UTC).isoformat()
        self.tables: dict[str, list[dict]] = {
            "meetings": [
                {
                    "id": "meeting-1",
                    "user_id": "user-1",
                    "subject": "Sprint planning",
                    "start_time": "2026-05-19T09:00:00Z",
                    "end_time": "2026-05-19T09:30:00Z",
                    "bot_status": "waiting_for_approval",
                    "approval_status": "pending",
                }
            ],
            "meeting_approvals": [],
            "bot_heartbeats": [
                {
                    "bot_instance_id": "bot-1",
                    "status": "ok",
                    "last_seen_at": now,
                }
            ],
        }

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

    async def upsert(
        self,
        path: str,
        payload: dict,
        on_conflict: str | None = None,
    ) -> list[dict]:
        if on_conflict:
            existing = next(
                (
                    row
                    for row in self.tables[path]
                    if row.get(on_conflict) == payload.get(on_conflict)
                ),
                None,
            )
            if existing:
                existing.update(payload)
                return [existing.copy()]

        row = payload.copy()
        row.setdefault("id", f"{path}-{len(self.tables[path]) + 1}")
        self.tables[path].append(row)
        return [row.copy()]

    async def patch(self, path: str, payload: dict, params: dict) -> list[dict]:
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


def test_upsert_bot_approval_stores_external_approval_id(monkeypatch):
    from app.internal.schemas import BotApprovalUpsertRequest
    from app.services import approvals

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(approvals, "supabase_gateway", fake)

    result = run(
        approvals.upsert_bot_approval(
            BotApprovalUpsertRequest(
                bot_approval_id="bot-approval-1",
                meeting_id="meeting-1",
                user_id="user-1",
                status="Pending",
                requested_via="teams",
                expires_at="2026-05-19T09:10:00Z",
            )
        )
    )

    assert result["bot_approval_id"] == "bot-approval-1"
    assert result["status"] == "pending"
    assert fake.tables["meetings"][0]["approval_status"] == "pending"


def test_list_user_approvals_includes_meeting_details(monkeypatch):
    from app.services import approvals

    fake = FakeSupabaseGateway()
    fake.tables["meeting_approvals"] = [
        {
            "id": "approval-1",
            "bot_approval_id": "bot-approval-1",
            "meeting_id": "meeting-1",
            "user_id": "user-1",
            "status": "pending",
            "requested_at": "2026-05-19T08:58:00Z",
            "expires_at": "2026-05-19T09:10:00Z",
            "decided_at": None,
            "decided_by": None,
            "decided_via": None,
            "requested_via": "teams",
        }
    ]
    monkeypatch.setattr(approvals, "supabase_gateway", fake)
    monkeypatch.setattr(approvals, "get_dev_user_id", lambda: "user-1")

    result = run(approvals.list_user_approvals())

    assert result[0]["id"] == "approval-1"
    assert result[0]["meeting"]["subject"] == "Sprint planning"
    assert result[0]["meeting"]["bot_status"] == "waiting_for_approval"


def test_decision_is_rejected_when_bot_is_offline(monkeypatch):
    from app.services import approvals

    fake = FakeSupabaseGateway()
    fake.tables["bot_heartbeats"][0]["last_seen_at"] = (
        datetime.now(UTC) - timedelta(minutes=20)
    ).isoformat()
    fake.tables["meeting_approvals"] = [
        {
            "id": "approval-1",
            "bot_approval_id": "bot-approval-1",
            "meeting_id": "meeting-1",
            "user_id": "user-1",
            "status": "pending",
        }
    ]
    monkeypatch.setattr(approvals, "supabase_gateway", fake)
    monkeypatch.setattr(approvals, "get_dev_user_id", lambda: "user-1")

    with pytest.raises(HTTPException) as exc:
        run(approvals.decide_user_approval("approval-1", "approve"))

    assert exc.value.status_code == 409
    assert fake.tables["meeting_approvals"][0]["status"] == "pending"


def test_decision_calls_bot_and_updates_approval(monkeypatch):
    from app.services import approvals

    fake = FakeSupabaseGateway()
    fake.tables["meeting_approvals"] = [
        {
            "id": "approval-1",
            "bot_approval_id": "bot-approval-1",
            "meeting_id": "meeting-1",
            "user_id": "user-1",
            "status": "pending",
        }
    ]
    calls = []

    async def fake_call_bot(bot_approval_id: str, decision: str, decided_by: str) -> dict:
        calls.append((bot_approval_id, decision, decided_by))
        return {"status": "Approved", "decided_via": "meetiq", "decided_by": decided_by}

    monkeypatch.setattr(approvals, "supabase_gateway", fake)
    monkeypatch.setattr(approvals, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(approvals, "_call_bot_decision_endpoint", fake_call_bot)

    result = run(approvals.decide_user_approval("approval-1", "approve"))

    assert calls == [("bot-approval-1", "approve", "user-1")]
    assert result["status"] == "approved"
    assert fake.tables["meetings"][0]["approval_status"] == "approved"
