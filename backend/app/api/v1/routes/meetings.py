from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.v1.schemas import (
    ManualJoinRequest,
    ManualJoinResponse,
    MeetingChatIndexResponse,
    MeetingChatRequest,
    MeetingChatResponse,
    UploadedRecordingJob,
    UploadedRecordingResponse,
)
from app.auth.current_user import CurrentUser, require_current_user
from app.services.ai_meetings import generate_meeting_intelligence
from app.services.bot_manual_join import manual_join_meeting
from app.services.meeting_chat import (
    chat_with_meeting_transcript,
    get_meeting_chat_index_status,
    get_meeting_chat_messages,
    index_meeting_transcript,
)
from app.services.meetings import (
    get_meeting_summary as load_meeting_summary,
    get_user_meeting,
    list_meeting_tasks,
    list_meeting_transcript,
    list_user_meetings,
)
from app.services.uploaded_recordings import create_uploaded_recording, get_upload_job
router = APIRouter(prefix="/meetings", tags=["meetings"])

@router.get("")
async def list_meetings(
    transcript_ready: bool = False,
    current_user: CurrentUser = require_current_user,
) -> dict[str, list]:
    return {
        "items": await list_user_meetings(
            transcript_ready=transcript_ready,
            user_id=current_user.user_id,
        )
    }

@router.post("/manual-join", response_model=ManualJoinResponse)
async def create_manual_join(payload: ManualJoinRequest) -> dict:
    return await manual_join_meeting(payload)

@router.post("/uploads", response_model=UploadedRecordingResponse)
async def upload_meeting_recording(
    title: str = Form(...),
    meeting_date: str | None = Form(default=None),
    transcript_text: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: CurrentUser = require_current_user,
) -> dict:
    return await create_uploaded_recording(
        user_id=current_user.user_id,
        title=title,
        meeting_date=meeting_date,
        file=file,
        transcript_text=transcript_text,
    )

@router.get("/uploads/{job_id}", response_model=UploadedRecordingJob)
async def get_meeting_upload_job(
    job_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict:
    return await get_upload_job(job_id, current_user.user_id)

@router.get("/{meeting_id}")
async def get_meeting(
    meeting_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict:
    meeting = await get_user_meeting(meeting_id, current_user.user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    return meeting

@router.get("/{meeting_id}/transcript")
async def get_meeting_transcript(
    meeting_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict[str, str | list]:
    return {
        "meeting_id": meeting_id,
        "segments": await list_meeting_transcript(meeting_id, current_user.user_id),
    }

@router.get("/{meeting_id}/summary")
async def get_meeting_summary(
    meeting_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict[str, str | list]:
    summary = await load_meeting_summary(meeting_id, current_user.user_id)
    return summary or {"meeting_id": meeting_id, "summary": "", "key_points": [], "decisions": []}

@router.get("/{meeting_id}/tasks")
async def get_meeting_tasks(
    meeting_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict[str, str | list]:
    return {
        "meeting_id": meeting_id,
        "items": await list_meeting_tasks(meeting_id, current_user.user_id),
    }

@router.post("/{meeting_id}/ai-intelligence")
async def create_meeting_ai_intelligence(
    meeting_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict:
    return await generate_meeting_intelligence(meeting_id, current_user.user_id)

@router.get("/{meeting_id}/chat/messages")
async def list_meeting_chat_messages(
    meeting_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict[str, str | list]:
    return {
        "meeting_id": meeting_id,
        "items": await get_meeting_chat_messages(meeting_id, current_user.user_id),
    }

@router.get("/{meeting_id}/chat/index-status", response_model=MeetingChatIndexResponse)
async def get_meeting_chat_index(
    meeting_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict:
    return await get_meeting_chat_index_status(meeting_id, current_user.user_id)

@router.post("/{meeting_id}/chat/index", response_model=MeetingChatIndexResponse)
async def create_meeting_chat_index(
    meeting_id: str,
    current_user: CurrentUser = require_current_user,
) -> dict:
    return await index_meeting_transcript(meeting_id, current_user.user_id)

@router.post("/{meeting_id}/chat", response_model=MeetingChatResponse)
async def create_meeting_chat_response(
    meeting_id: str,
    payload: MeetingChatRequest,
    current_user: CurrentUser = require_current_user,
) -> dict:
    return await chat_with_meeting_transcript(meeting_id, payload.message, current_user.user_id)
