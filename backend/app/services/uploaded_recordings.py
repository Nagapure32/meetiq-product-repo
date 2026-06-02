import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.db.supabase import supabase_gateway
from app.services.ai_meetings import generate_meeting_intelligence
from app.services.meeting_chat import index_meeting_transcript

ALLOWED_UPLOAD_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "video/mp4",
    "video/quicktime",
    "video/webm",
}
UPLOAD_SOURCE_TYPE = "uploaded_recording"
TRANSCRIPTION_NOT_CONFIGURED = "Transcription provider is not configured."
MEDIA_STORAGE_NOT_CONFIGURED = "Azure Blob media storage is not configured."


@dataclass(frozen=True)
class StoredUpload:
    blob_name: str
    blob_url: str
    content: bytes


async def create_uploaded_recording(
    user_id: str,
    title: str,
    meeting_date: str | None,
    file: UploadFile,
    transcript_text: str | None = None,
) -> dict[str, Any]:
    _validate_upload(file)
    upload_id = str(uuid4())
    stored_upload = await _store_uploaded_file(upload_id, user_id, file)
    start_time = _parse_meeting_date(meeting_date)
    now = datetime.now(UTC).isoformat()

    meeting = await _create_uploaded_meeting(
        user_id=user_id,
        title=title,
        upload_id=upload_id,
        start_time=start_time,
        uploaded_media_url=stored_upload.blob_url,
        now=now,
    )
    job = await _create_upload_job(
        meeting_id=meeting["id"],
        user_id=user_id,
        original_filename=file.filename or "recording",
        content_type=file.content_type,
        storage_path=stored_upload.blob_name,
        now=now,
    )

    try:
        clean_transcript = (transcript_text or "").strip()
        if not clean_transcript:
            await _patch_meeting_processing_status(meeting["id"], "transcribing")
            await _patch_job(
                job["id"],
                {
                    "status": "transcribing",
                    "error_message": None,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
            clean_transcript = await _transcribe_uploaded_file(
                media_content=stored_upload.content,
                original_filename=file.filename or "recording",
                content_type=file.content_type,
            )

        segments = await _store_transcript_text(meeting["id"], clean_transcript)
        await _patch_meeting_processing_status(meeting["id"], "transcript_ready")
        await _patch_job(
            job["id"],
            {
                "status": "transcript_ready",
                "transcript_segment_count": len(segments),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        await generate_meeting_intelligence(meeting["id"], user_id)
        await index_meeting_transcript(meeting["id"], user_id)
    except Exception as exc:
        await _patch_meeting_processing_status(meeting["id"], "failed")
        job = await _patch_job(
            job["id"],
            {
                "status": "failed",
                "error_message": str(exc),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        return {"status": "failed", "meeting": meeting, "job": job}

    await _patch_meeting_processing_status(meeting["id"], "ready")
    job = await _patch_job(
        job["id"],
        {
            "status": "ready",
            "error_message": None,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )
    return {"status": "ready", "meeting": meeting, "job": job}


async def get_upload_job(job_id: str, user_id: str) -> dict[str, Any]:
    rows = await supabase_gateway.get(
        "meeting_upload_jobs",
        {
            "select": "*",
            "id": f"eq.{job_id}",
            "user_id": f"eq.{user_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload job not found.")
    return rows[0]


def _validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload filename is required.",
        )
    if file.content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload must be a supported audio or video file.",
        )


async def _transcribe_uploaded_file(
    media_content: bytes,
    original_filename: str,
    content_type: str | None,
) -> str:
    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=TRANSCRIPTION_NOT_CONFIGURED,
        )

    url = (
        f"https://{settings.azure_speech_region}.api.cognitive.microsoft.com/"
        "speechtotext/transcriptions:transcribe"
    )
    definition = {
        "locales": [settings.azure_speech_default_language],
        "profanityFilterMode": "Masked",
    }
    files = {
        "audio": (
            original_filename,
            media_content,
            content_type or "application/octet-stream",
        ),
        "definition": (None, json.dumps(definition), "application/json"),
    }
    headers = {"Ocp-Apim-Subscription-Key": settings.azure_speech_key}
    params = {"api-version": settings.azure_speech_api_version}

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(url, headers=headers, params=params, files=files)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Azure Speech transcription request failed: {exc}",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Azure Speech transcription failed.",
                "status_code": response.status_code,
                "response": response.text,
            },
        )

    return _transcription_response_to_text(response.json())


def _transcription_response_to_text(data: dict[str, Any]) -> str:
    phrase_lines = _phrase_lines(data.get("phrases"))
    if phrase_lines:
        return "\n".join(phrase_lines)

    combined_phrases = data.get("combinedPhrases")
    if isinstance(combined_phrases, list):
        combined_text = " ".join(
            str(phrase.get("text") or phrase.get("display") or "").strip()
            for phrase in combined_phrases
            if isinstance(phrase, dict)
        ).strip()
        if combined_text:
            return combined_text

    text = str(data.get("text") or data.get("display") or "").strip()
    if text:
        return text

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Azure Speech did not return transcript text.",
    )


def _phrase_lines(phrases: Any) -> list[str]:
    if not isinstance(phrases, list):
        return []

    lines = []
    for index, phrase in enumerate(phrases, start=1):
        if not isinstance(phrase, dict):
            continue
        text = str(phrase.get("text") or phrase.get("display") or "").strip()
        if not text:
            continue
        speaker = phrase.get("speaker") or phrase.get("channel")
        speaker_name = f"Speaker {speaker}" if speaker is not None else f"Speaker {index}"
        lines.append(f"{speaker_name}: {text}")
    return lines


async def _store_uploaded_file(upload_id: str, user_id: str, file: UploadFile) -> StoredUpload:
    content = await file.read()
    blob_name = _uploaded_media_blob_name(
        user_id=user_id,
        upload_id=upload_id,
        original_filename=file.filename or "recording",
    )
    blob_url = _upload_media_to_azure_blob(
        blob_name=blob_name,
        content=content,
        content_type=file.content_type,
    )
    return StoredUpload(blob_name=blob_name, blob_url=blob_url, content=content)


def _upload_media_to_azure_blob(blob_name: str, content: bytes, content_type: str | None) -> str:
    if not settings.azure_storage_connection_string or not settings.azure_media_container:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=MEDIA_STORAGE_NOT_CONFIGURED,
        )

    try:
        from azure.core.exceptions import AzureError
        from azure.storage.blob import BlobServiceClient, ContentSettings
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure Blob Storage client is not installed.",
        ) from exc

    blob_service = BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string,
    )
    blob_client = blob_service.get_blob_client(
        container=settings.azure_media_container,
        blob=blob_name,
    )
    try:
        blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings=ContentSettings(
                content_type=content_type or "application/octet-stream",
            ),
        )
    except AzureError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Azure Blob media upload failed: {exc}",
        ) from exc
    return blob_client.url


def _uploaded_media_blob_name(user_id: str, upload_id: str, original_filename: str) -> str:
    prefix = settings.azure_media_prefix.strip("/")
    safe_filename = _safe_blob_filename(original_filename)
    path = f"{user_id}/{upload_id}-{safe_filename}"
    return f"{prefix}/{path}" if prefix else path


def _safe_blob_filename(filename: str) -> str:
    name = Path(filename).name.strip() or "recording"
    suffix = Path(name).suffix
    stem = name[: -len(suffix)] if suffix else name
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")
    safe_suffix = re.sub(r"[^A-Za-z0-9.]+", "", suffix)
    return f"{safe_stem or 'recording'}{safe_suffix}"


def _parse_meeting_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="meeting_date must be an ISO date/time.",
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


async def _create_uploaded_meeting(
    user_id: str,
    title: str,
    upload_id: str,
    start_time: datetime,
    uploaded_media_url: str,
    now: str,
) -> dict[str, Any]:
    subject = title.strip() or "Uploaded recording"
    rows = await supabase_gateway.insert(
        "meetings",
        {
            "user_id": user_id,
            "graph_event_id": f"upload:{upload_id}",
            "subject": subject,
            "organizer_email": None,
            "join_url": None,
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(minutes=1)).isoformat(),
            "status": "uploaded",
            "bot_status": "not_applicable",
            "approval_status": "not_required",
            "source_type": UPLOAD_SOURCE_TYPE,
            "processing_status": "uploaded",
            "uploaded_media_url": uploaded_media_url,
            "created_at": now,
            "updated_at": now,
        },
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase did not return the uploaded meeting.",
        )
    return rows[0]


async def _create_upload_job(
    meeting_id: str,
    user_id: str,
    original_filename: str,
    content_type: str | None,
    storage_path: str,
    now: str,
) -> dict[str, Any]:
    rows = await supabase_gateway.insert(
        "meeting_upload_jobs",
        {
            "meeting_id": meeting_id,
            "user_id": user_id,
            "status": "uploaded",
            "original_filename": original_filename,
            "content_type": content_type,
            "storage_path": storage_path,
            "error_message": None,
            "transcript_segment_count": 0,
            "created_at": now,
            "updated_at": now,
        },
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase did not return the upload job.",
        )
    return rows[0]


async def _store_transcript_text(meeting_id: str, transcript_text: str) -> list[dict[str, Any]]:
    rows = []
    for index, line in enumerate(_split_transcript_lines(transcript_text), start=1):
        speaker, text = _parse_transcript_line(line)
        if not text:
            continue
        rows.append(
            {
                "meeting_id": meeting_id,
                "sequence": index,
                "speaker": speaker,
                "source_id": speaker,
                "language": None,
                "text": text,
            }
        )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transcript text did not contain any usable lines.",
        )
    return await supabase_gateway.insert("transcript_segments", rows)


def _split_transcript_lines(transcript_text: str) -> list[str]:
    return [line.strip() for line in transcript_text.splitlines() if line.strip()]


def _parse_transcript_line(line: str) -> tuple[str | None, str]:
    if ":" not in line:
        return None, line.strip()
    speaker, text = line.split(":", 1)
    clean_speaker = speaker.strip() or None
    return clean_speaker, text.strip()


async def _patch_job(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    rows = await supabase_gateway.patch(
        "meeting_upload_jobs",
        payload,
        params={"id": f"eq.{job_id}", "limit": "1"},
    )
    return rows[0] if rows else {"id": job_id, **payload}


async def _patch_meeting_processing_status(meeting_id: str, processing_status: str) -> None:
    await supabase_gateway.patch(
        "meetings",
        {
            "processing_status": processing_status,
            "status": processing_status,
            "updated_at": datetime.now(UTC).isoformat(),
        },
        params={"id": f"eq.{meeting_id}", "limit": "1"},
    )
