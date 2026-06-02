from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_bot_api_key(authorization: str | None = Header(default=None)) -> None:
    if not settings.enable_bot_internal_apis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internal bot APIs are disabled.",
        )

    expected_key = settings.bot_internal_api_key
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BOT_INTERNAL_API_KEY is not configured.",
        )

    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or token != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bot service credentials.",
        )

