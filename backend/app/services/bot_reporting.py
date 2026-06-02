from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.db.supabase import supabase_gateway
from app.internal.schemas import (
    BotApprovalDecisionRequest,
    BotMeetingStatusRequest,
    BotMeetingUpsertRequest,
    BotTranscriptRequest,
)

DECISION_TO_STATUS = {
    "approve": "approved",
    "approved": "approved",
    "reject": "rejected",
    "rejected": "rejected",
}


def _isoformat(value: datetime) -> str:
    return value.isoformat()


async def upsert_bot_meeting(payload: BotMeetingUpsertRequest) -> dict:
    updated_at = datetime.now(UTC).isoformat()
    rows = await supabase_gateway.upsert(
        "meetings",
        {
            "user_id": payload.user_id,
            "organization_id": payload.organization_id,
            "graph_event_id": payload.graph_event_id,
            "subject": payload.subject,
            "organizer_email": payload.organizer_email,
            "join_url": payload.join_url,
            "start_time": _isoformat(payload.start_time),
            "end_time": _isoformat(payload.end_time),
            "status": payload.status,
            "bot_status": payload.bot_status,
            "approval_status": payload.approval_status,
            "updated_at": updated_at,
        },
        on_conflict="user_id,graph_event_id",
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase did not return the upserted meeting.",
        )

    meeting = rows[0]
    await _upsert_shared_meeting_intent(payload, meeting, updated_at)

    return meeting


async def _upsert_shared_meeting_intent(
    payload: BotMeetingUpsertRequest,
    meeting: dict,
    updated_at: str,
) -> None:
    if not payload.dedupe_key:
        return

    instances = await supabase_gateway.upsert(
        "meeting_instances",
        {
            "dedupe_key": payload.dedupe_key,
            "join_url": payload.join_url,
            "subject": payload.subject,
            "organizer_email": payload.organizer_email,
            "start_time": _isoformat(payload.start_time),
            "end_time": _isoformat(payload.end_time),
            "bot_status": payload.bot_status,
            "updated_at": updated_at,
        },
        on_conflict="dedupe_key",
    )

    if not instances:
        return

    instance_id = instances[0].get("id")
    meeting_id = meeting.get("id")
    if not instance_id or not meeting_id:
        return

    await supabase_gateway.upsert(
        "meeting_user_intents",
        {
            "meeting_instance_id": instance_id,
            "user_id": payload.user_id,
            "meeting_id": meeting_id,
            "graph_event_id": payload.graph_event_id,
            "calendar_email": payload.calendar_user_email or "",
            "approval_status": payload.approval_status,
            "updated_at": updated_at,
        },
        on_conflict="meeting_instance_id,user_id",
    )


async def update_bot_meeting_status(
    meeting_id: str,
    payload: BotMeetingStatusRequest,
) -> dict:
    update_payload = payload.model_dump(exclude_none=True)
    if not update_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one meeting status field is required.",
        )

    update_payload["updated_at"] = datetime.now(UTC).isoformat()
    rows = await supabase_gateway.patch(
        "meetings",
        update_payload,
        params={"id": f"eq.{meeting_id}", "limit": "1"},
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting was not found.",
        )

    return rows[0]


async def record_bot_transcript(payload: BotTranscriptRequest) -> list[dict]:
    rows_to_insert = []
    for segment in payload.segments:
        rows_to_insert.append(
            {
                "meeting_id": payload.meeting_id,
                "sequence": segment.sequence,
                "speaker": segment.speaker,
                "source_id": segment.source_id,
                "speaker_participant_id": segment.speaker_participant_id,
                "speaker_aad_user_id": segment.speaker_aad_user_id,
                "speaker_email": segment.speaker_email,
                "speaker_user_principal_name": segment.speaker_user_principal_name,
                "language": segment.language,
                "text": segment.text,
                "started_at": _isoformat(segment.started_at) if segment.started_at else None,
                "ended_at": _isoformat(segment.ended_at) if segment.ended_at else None,
            }
        )

    rows = await supabase_gateway.insert("transcript_segments", rows_to_insert)
    last_seen_at = datetime.now(UTC).isoformat()
    for segment in payload.segments:
        if not segment.source_id:
            continue
        participant_payload = {
            "meeting_id": payload.meeting_id,
            "source_id": segment.source_id,
            "last_seen_at": last_seen_at,
        }
        participant_payload.update(
            {
                key: value
                for key, value in {
                    "participant_id": segment.speaker_participant_id,
                    "aad_user_id": segment.speaker_aad_user_id,
                    "display_name": segment.speaker,
                    "email": segment.speaker_email,
                    "user_principal_name": segment.speaker_user_principal_name,
                }.items()
                if value is not None
            }
        )
        await supabase_gateway.upsert(
            "meeting_participants",
            participant_payload,
            on_conflict="meeting_id,source_id",
        )
    return rows

async def record_bot_approval_decision(
    approval_id: str,
    payload: BotApprovalDecisionRequest,
) -> dict:
    decided_at = datetime.now(UTC).isoformat()
    decision = DECISION_TO_STATUS.get(payload.decision.lower(), payload.decision.lower())
    rows = await supabase_gateway.patch(
        "meeting_approvals",
        {
            "status": decision,
            "decided_at": decided_at,
            "decided_by": payload.decided_by,
            "decided_via": payload.decided_via,
            "updated_at": decided_at,
        },
        params={"id": f"eq.{approval_id}", "limit": "1"},
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval was not found.",
        )

    approval = rows[0]
    meeting_id = approval.get("meeting_id")
    if meeting_id:
        await supabase_gateway.patch(
            "meetings",
            {
                "approval_status": decision,
                "updated_at": decided_at,
            },
            params={"id": f"eq.{meeting_id}", "limit": "1"},
        )
    return approval
