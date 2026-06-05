import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings

class CurrentUser(BaseModel):
    user_id: str
    email: str | None = None
    auth_source: Literal["supabase", "dev"]

async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() == "bearer" and token:
        return await _current_user_from_supabase_token(token)

    if _can_use_dev_user_fallback():
        return CurrentUser(user_id=settings.dev_user_id, auth_source="dev")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required.",
    )

require_current_user = Depends(get_current_user)

def _can_use_dev_user_fallback() -> bool:
    return (
        settings.app_env.lower() in {"development", "dev", "local", "test"}
        and settings.allow_dev_user_fallback
        and not settings.auth_required
        and bool(settings.dev_user_id)
    )

async def _current_user_from_supabase_token(token: str) -> CurrentUser:
    try:
        return _current_user_from_supabase_jwt(token)
    except HTTPException as jwt_error:
        return await _current_user_from_supabase_auth_api(token, jwt_error)


def _current_user_from_supabase_jwt(token: str) -> CurrentUser:
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPABASE_JWT_SECRET is not configured.",
        )
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise _invalid_token() from exc

    header = _decode_json_segment(header_segment)
    if header.get("alg") != "HS256":
        raise _invalid_token()

    expected_signature = hmac.new(
        settings.supabase_jwt_secret.encode("utf-8"),
        f"{header_segment}.{payload_segment}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    actual_signature = _decode_segment(signature_segment)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise _invalid_token()

    payload = _decode_json_segment(payload_segment)
    _validate_supabase_claims(payload)

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise _invalid_token()

    email = payload.get("email")
    return CurrentUser(
        user_id=user_id,
        email=email if isinstance(email, str) else None,
        auth_source="supabase",
    )


def _validate_supabase_claims(payload: dict) -> None:
    exp = payload.get("exp")
    if type(exp) is not int or datetime.now(UTC).timestamp() >= exp:
        raise _invalid_token()

    aud = payload.get("aud")
    if aud != "authenticated":
        raise _invalid_token()

    expected_issuer = _expected_supabase_issuer()
    if expected_issuer and payload.get("iss") != expected_issuer:
        raise _invalid_token()

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise _invalid_token()

def _expected_supabase_issuer() -> str | None:
    if not settings.supabase_url:
        return None
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


async def _current_user_from_supabase_auth_api(
    token: str,
    jwt_error: HTTPException,
) -> CurrentUser:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise jwt_error

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.supabase_anon_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.HTTPError as exc:
        raise jwt_error from exc

    if response.status_code >= 400:
        raise jwt_error
    data = response.json()
    user_id = data.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise jwt_error

    email = data.get("email")
    return CurrentUser(
        user_id=user_id,
        email=email if isinstance(email, str) else None,
        auth_source="supabase",
    )

def _decode_json_segment(segment: str) -> dict:
    try:
        decoded = _decode_segment(segment)
        data = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _invalid_token() from exc

    if not isinstance(data, dict):
        raise _invalid_token()
    return data

def _decode_segment(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(f"{segment}{padding}".encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise _invalid_token() from exc

def _invalid_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token.",
    )
