from datetime import UTC, datetime
import re
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

import httpx
from fastapi import HTTPException, status

from app.api.v1.schemas import ManualJoinRequest
from app.core.config import settings
from app.db.supabase import supabase_gateway


async def manual_join_meeting(payload: ManualJoinRequest) -> dict[str, Any]:
    meeting = await _get_meeting(payload.meeting_id) if payload.meeting_id else None
    bot_payload = _build_bot_join_payload(payload, meeting)

    result = await _call_bot_join_endpoint(bot_payload)
    if meeting:
        await _mark_meeting_joining(meeting["id"])

    return {
        "status": "accepted",
        "meeting_id": meeting["id"] if meeting else None,
        "call_id": result.get("callId"),
        "state": result.get("state"),
        "join_mode": result.get("joinMode"),
        "media_mode": result.get("mediaMode"),
        "message": result.get("message") or "Manual join request was accepted by the Teams bot.",
    }


async def _get_meeting(meeting_id: str | None) -> dict[str, Any]:
    rows = await supabase_gateway.get(
        "meetings",
        {
            "select": "id,join_url,bot_status,status",
            "id": f"eq.{meeting_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    return rows[0]


def _build_bot_join_payload(
    payload: ManualJoinRequest,
    meeting: dict[str, Any] | None,
) -> dict[str, Any]:
    raw_join_web_url = _clean(payload.join_web_url) or _clean(meeting.get("join_url") if meeting else None)
    extracted_details = _extract_join_details(raw_join_web_url)
    join_web_url = _extract_join_web_url(raw_join_web_url)
    join_meeting_id = _clean(payload.join_meeting_id) or extracted_details.get("joinMeetingId")
    passcode = _clean(payload.passcode) or extracted_details.get("passcode")

    if not join_web_url and not (join_meeting_id and passcode):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide a meeting or Teams join details before starting manual join.",
        )

    bot_payload: dict[str, Any] = {
        "useServiceHostedMedia": payload.use_service_hosted_media,
    }
    if join_web_url:
        bot_payload["joinWebUrl"] = join_web_url
    if passcode:
        bot_payload["passcode"] = passcode
    if join_meeting_id:
        bot_payload["joinMeetingId"] = join_meeting_id
    return bot_payload


async def _call_bot_join_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.teams_bot_base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TEAMS_BOT_BASE_URL is not configured.",
        )

    headers = {"Authorization": f"Bearer {settings.bot_internal_api_key}"} if settings.bot_internal_api_key else {}
    url = f"{settings.teams_bot_base_url.rstrip('/')}/api/join"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The Teams bot manual join endpoint could not be reached.",
        ) from exc

    data = _safe_json(response)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=data.get("error") or data.get("message") or "The Teams bot rejected manual join.",
        )
    return data


async def _mark_meeting_joining(meeting_id: str) -> None:
    await supabase_gateway.patch(
        "meetings",
        {
            "bot_status": "joining",
            "status": "joining",
            "updated_at": datetime.now(UTC).isoformat(),
        },
        params={"id": f"eq.{meeting_id}", "limit": "1"},
    )


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _extract_join_details(value: str | None) -> dict[str, str]:
    if not value:
        return {}

    details: dict[str, str] = {}
    for key, raw_value in _iter_join_detail_params(value):
        normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
        cleaned_value = _clean(unquote(raw_value))
        if not cleaned_value:
            continue
        if normalized_key in {"meetingid", "joinmeetingid"} and "joinMeetingId" not in details:
            details["joinMeetingId"] = cleaned_value
        if (
            normalized_key in {"passcode", "meetingpasscode", "joinpasscode", "pwd", "password"}
            and "passcode" not in details
        ):
            details["passcode"] = cleaned_value

    if "joinMeetingId" not in details:
        meeting_id = _extract_labeled_value(
            value,
            r"\b(?:meeting\s*id|join\s*meeting\s*id)\s*[:#]?\s*([0-9][0-9\s-]{5,}[0-9])",
        )
        if meeting_id:
            details["joinMeetingId"] = meeting_id

    if "passcode" not in details:
        passcode = _extract_labeled_value(
            value,
            r"\b(?:pass\s*code|passcode|password|pwd)\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9._~-]{1,})",
        )
        if passcode:
            details["passcode"] = passcode

    return details


def _extract_join_web_url(value: str | None) -> str | None:
    cleaned = _clean(value)
    if not cleaned:
        return None

    if cleaned.startswith(("http://", "https://")):
        return cleaned

    match = re.search(r"https?://teams\.microsoft\.com/[^\s<>\"]+", cleaned, flags=re.IGNORECASE)
    return match.group(0).rstrip(".,);]") if match else None


def _iter_join_detail_params(value: str) -> list[tuple[str, str]]:
    parsed = urlsplit(value)
    pairs = parse_qsl(parsed.query, keep_blank_values=False)

    fragment = parsed.fragment
    if "?" in fragment:
        fragment = fragment.split("?", 1)[1]
    pairs.extend(parse_qsl(fragment, keep_blank_values=False))

    return pairs


def _extract_labeled_value(value: str, pattern: str) -> str | None:
    match = re.search(pattern, value, flags=re.IGNORECASE)
    return _clean(match.group(1)) if match else None


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
