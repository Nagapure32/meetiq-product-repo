from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: int | float | str
    helper: str | None = None


class DashboardOverview(BaseModel):
    metrics: list[DashboardMetric]
    upcoming_meetings: list[dict]
    recent_action_items: list[dict]
    bot_status: dict
    task_summary: dict = {}
    attention_items: list[dict] = []
    recent_activity: list[dict] = []


class MeetingAssistantSettings(BaseModel):
    user_id: str | None = None
    auto_join_enabled: bool = False
    require_approval: bool = True
    approval_lead_minutes: int = 2
    look_ahead_minutes: int = 15
    join_early_seconds: int = 0
    max_late_join_minutes: int = 10
    leave_grace_minutes: int = 2
    use_service_hosted_media: bool = False


class TranscriptionSettings(BaseModel):
    auto_detect_enabled: bool = True
    language_id_mode: str = "Continuous"
    default_language: str = "en-IN"
    candidate_languages: list[str] = ["en-IN", "en-US", "hi-IN", "mr-IN"]


class UserBootstrapRequest(BaseModel):
    email: str | None = None
    tenant_id: str | None = None
    aad_user_id: str | None = None


class UserBootstrapResponse(BaseModel):
    user_id: str
    calendar_connection_status: str


class UserOnboardingStatus(BaseModel):
    user_id: str
    onboarding_completed: bool
    onboarding_completed_at: str | None = None
    calendar_connection_status: str | None = None
    auto_join_enabled: bool = False


class ManualJoinRequest(BaseModel):
    meeting_id: str | None = None
    join_web_url: str | None = None
    join_meeting_id: str | None = None
    passcode: str | None = None
    use_service_hosted_media: bool = False


class ManualJoinResponse(BaseModel):
    status: str
    meeting_id: str | None = None
    call_id: str | None = None
    state: str | None = None
    join_mode: str | None = None
    media_mode: str | None = None
    message: str


class UploadedRecordingJob(BaseModel):
    id: str
    meeting_id: str
    user_id: str
    status: str
    original_filename: str
    content_type: str | None = None
    transcript_segment_count: int = 0
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UploadedRecordingResponse(BaseModel):
    status: str
    meeting: dict
    job: UploadedRecordingJob


class MeetingChatRequest(BaseModel):
    message: str


class MeetingChatSource(BaseModel):
    id: str
    chunk_text: str
    speaker: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    source_segment_ids: list[str] = []


class MeetingChatResponse(BaseModel):
    meeting_id: str
    answer: str
    sources: list[MeetingChatSource] = []


class MeetingChatIndexResponse(BaseModel):
    meeting_id: str
    status: str
    indexed_chunk_count: int = 0
    transcript_segment_count: int = 0
    error_message: str | None = None


class TaskAssignee(BaseModel):
    user_id: str
    display_name: str | None = None
    email: str | None = None
    role: str = "collaborator"


class TaskMeeting(BaseModel):
    id: str
    subject: str
    start_time: str | None = None
    end_time: str | None = None
    organizer_email: str | None = None


class TaskItem(BaseModel):
    id: str
    organization_id: str | None = None
    owner_user_id: str
    assignee_user_id: str | None = None
    meeting_id: str | None = None
    action_item_id: str | None = None
    title: str
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    due_date: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    assignees: list[TaskAssignee] = []
    meeting: TaskMeeting | None = None


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    due_date: str | None = None
    meeting_id: str | None = None
    action_item_id: str | None = None
    assignee_user_ids: list[str] = []


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None
    meeting_id: str | None = None
    action_item_id: str | None = None
    assignee_user_ids: list[str] | None = None


class ApprovalMeeting(BaseModel):
    id: str
    subject: str
    start_time: str
    end_time: str
    bot_status: str | None = None
    approval_status: str | None = None
    organizer_email: str | None = None


class ApprovalItem(BaseModel):
    id: str
    bot_approval_id: str | None = None
    meeting_id: str
    user_id: str
    status: str
    requested_via: str | None = None
    requested_at: str | None = None
    expires_at: str | None = None
    decided_at: str | None = None
    decided_by: str | None = None
    decided_via: str | None = None
    meeting: ApprovalMeeting | None = None
