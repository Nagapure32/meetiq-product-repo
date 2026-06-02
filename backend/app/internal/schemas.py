from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BotCalendarUser(BaseModel):
      user_id: str
      tenant_id: str | None = None
      aad_user_id: str | None = None
      email: str
      auto_join_enabled: bool = True
      require_approval: bool = True
      look_ahead_minutes: int = 15
      approval_lead_minutes: int = 2
      join_early_seconds: int = 0
      max_late_join_minutes: int = 10
      leave_grace_minutes: int = 2


class BotHeartbeatRequest(BaseModel):
      bot_instance_id: str
      version: str | None = None
      status: str = "ok"
      payload: dict[str, Any] = Field(default_factory=dict)


class BotEventRequest(BaseModel):
      bot_instance_id: str
      user_id: str | None = None
      meeting_id: str | None = None
      event_type: str
      severity: str = "info"
      message: str
      payload: dict[str, Any] = Field(default_factory=dict)


class BotMeetingUpsertRequest(BaseModel):
      user_id: str
      graph_event_id: str
      dedupe_key: str | None = None
      calendar_user_email: str | None = None
      subject: str
      start_time: datetime
      end_time: datetime
      organization_id: str | None = None
      organizer_email: str | None = None
      join_url: str | None = None
      status: str = "detected"
      bot_status: str = "not_started"
      approval_status: str = "not_required"


class BotMeetingStatusRequest(BaseModel):
      status: str | None = None
      bot_status: str | None = None
      approval_status: str | None = None


class BotTranscriptSegment(BaseModel):
      sequence: int | None = None
      speaker: str | None = None
      source_id: str | None = None
      speaker_participant_id: str | None = None
      speaker_aad_user_id: str | None = None
      speaker_email: str | None = None
      speaker_user_principal_name: str | None = None
      language: str | None = None
      text: str
      started_at: datetime | None = None
      ended_at: datetime | None = None


class BotTranscriptRequest(BaseModel):
      meeting_id: str
      segments: list[BotTranscriptSegment] = Field(min_length=1)


class BotApprovalDecisionRequest(BaseModel):
      decision: str
      decided_by: str | None = None
      decided_via: str = "bot"


class BotApprovalUpsertRequest(BaseModel):
      bot_approval_id: str
      meeting_id: str
      user_id: str
      status: str = "pending"
      requested_via: str | None = None
      expires_at: datetime | None = None
