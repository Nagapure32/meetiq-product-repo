import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _jwt(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url(signature)}"


def _client() -> TestClient:
    from app.auth.current_user import CurrentUser, require_current_user

    app = FastAPI()

    @app.get("/whoami")
    async def whoami(current_user: CurrentUser = require_current_user) -> dict:
        return current_user.model_dump()

    return TestClient(app)


def test_current_user_uses_dev_user_when_no_bearer_token_and_fallback_enabled(monkeypatch):
    from app.auth import current_user

    monkeypatch.setattr(current_user.settings, "app_env", "development")
    monkeypatch.setattr(current_user.settings, "dev_user_id", "dev-user-id")
    monkeypatch.setattr(current_user.settings, "auth_required", False)
    monkeypatch.setattr(current_user.settings, "allow_dev_user_fallback", True)

    response = _client().get("/whoami")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "dev-user-id",
        "email": None,
        "auth_source": "dev",
    }


def test_current_user_rejects_missing_token_when_auth_required(monkeypatch):
    from app.auth import current_user

    monkeypatch.setattr(current_user.settings, "dev_user_id", "dev-user-id")
    monkeypatch.setattr(current_user.settings, "auth_required", True)
    monkeypatch.setattr(current_user.settings, "allow_dev_user_fallback", False)

    response = _client().get("/whoami")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication is required."


def test_current_user_rejects_dev_fallback_outside_development(monkeypatch):
    from app.auth import current_user

    monkeypatch.setattr(current_user.settings, "app_env", "production")
    monkeypatch.setattr(current_user.settings, "dev_user_id", "dev-user-id")
    monkeypatch.setattr(current_user.settings, "auth_required", False)
    monkeypatch.setattr(current_user.settings, "allow_dev_user_fallback", True)

    response = _client().get("/whoami")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication is required."


def test_current_user_accepts_valid_supabase_jwt(monkeypatch):
    from app.auth import current_user

    secret = "test-secret"
    expires_at = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
    token = _jwt(
        {
            "sub": "auth-user-id",
            "email": "person@example.com",
            "exp": expires_at,
            "aud": "authenticated",
        },
        secret,
    )
    monkeypatch.setattr(current_user.settings, "supabase_jwt_secret", secret)
    monkeypatch.setattr(current_user.settings, "supabase_url", "")
    monkeypatch.setattr(current_user.settings, "supabase_anon_key", "")
    monkeypatch.setattr(current_user.settings, "auth_required", True)
    monkeypatch.setattr(current_user.settings, "allow_dev_user_fallback", False)

    response = _client().get("/whoami", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "auth-user-id",
        "email": "person@example.com",
        "auth_source": "supabase",
    }


def test_current_user_rejects_invalid_signature(monkeypatch):
    from app.auth import current_user

    expires_at = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
    token = _jwt({"sub": "auth-user-id", "exp": expires_at}, "wrong-secret")
    monkeypatch.setattr(current_user.settings, "supabase_jwt_secret", "expected-secret")
    monkeypatch.setattr(current_user.settings, "supabase_url", "")
    monkeypatch.setattr(current_user.settings, "supabase_anon_key", "")
    monkeypatch.setattr(current_user.settings, "auth_required", True)
    monkeypatch.setattr(current_user.settings, "allow_dev_user_fallback", False)

    response = _client().get("/whoami", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token."


def test_current_user_accepts_expected_issuer_when_supabase_url_is_configured(monkeypatch):
    from app.auth import current_user

    secret = "test-secret"
    expires_at = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
    token = _jwt(
        {
            "sub": "auth-user-id",
            "email": "person@example.com",
            "exp": expires_at,
            "aud": "authenticated",
            "iss": "https://project.supabase.co/auth/v1",
        },
        secret,
    )
    monkeypatch.setattr(current_user.settings, "supabase_jwt_secret", secret)
    monkeypatch.setattr(current_user.settings, "supabase_url", "https://project.supabase.co")
    monkeypatch.setattr(current_user.settings, "supabase_anon_key", "")
    monkeypatch.setattr(current_user.settings, "auth_required", True)
    monkeypatch.setattr(current_user.settings, "allow_dev_user_fallback", False)

    response = _client().get("/whoami", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "auth-user-id",
        "email": "person@example.com",
        "auth_source": "supabase",
    }


def test_current_user_rejects_token_without_exp(monkeypatch):
    from app.auth import current_user

    token = _jwt({"sub": "auth-user-id", "aud": "authenticated"}, "test-secret")
    monkeypatch.setattr(current_user.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(current_user.settings, "supabase_url", "")
    monkeypatch.setattr(current_user.settings, "supabase_anon_key", "")
    monkeypatch.setattr(current_user.settings, "auth_required", True)
    monkeypatch.setattr(current_user.settings, "allow_dev_user_fallback", False)

    response = _client().get("/whoami", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token."


def test_current_user_rejects_token_with_wrong_audience(monkeypatch):
    from app.auth import current_user

    expires_at = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
    token = _jwt(
        {"sub": "auth-user-id", "exp": expires_at, "aud": "anon"},
        "test-secret",
    )
    monkeypatch.setattr(current_user.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(current_user.settings, "supabase_url", "")
    monkeypatch.setattr(current_user.settings, "supabase_anon_key", "")
    monkeypatch.setattr(current_user.settings, "auth_required", True)
    monkeypatch.setattr(current_user.settings, "allow_dev_user_fallback", False)

    response = _client().get("/whoami", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token."


def test_current_user_rejects_token_with_wrong_issuer_when_supabase_url_is_configured(monkeypatch):
    from app.auth import current_user

    expires_at = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
    token = _jwt(
        {
            "sub": "auth-user-id",
            "exp": expires_at,
            "aud": "authenticated",
            "iss": "https://other-project.supabase.co/auth/v1",
        },
        "test-secret",
    )
    monkeypatch.setattr(current_user.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(current_user.settings, "supabase_url", "https://project.supabase.co")
    monkeypatch.setattr(current_user.settings, "supabase_anon_key", "")
    monkeypatch.setattr(current_user.settings, "auth_required", True)
    monkeypatch.setattr(current_user.settings, "allow_dev_user_fallback", False)

    response = _client().get("/whoami", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token."
