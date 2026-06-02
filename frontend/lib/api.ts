export type DashboardMetric = {
  label: string;
  value: number | string;
  helper?: string | null;
};

export type DashboardOverview = {
  metrics: DashboardMetric[];
  upcoming_meetings: DashboardMeeting[];
  recent_action_items: DashboardTask[];
  bot_status: {
    status: string;
    message: string;
  };
  task_summary?: {
    open: number;
    completed: number;
    overdue: number;
    created_today: number;
    completion_rate: number;
    weekly_meeting_hours?: number;
    meetings_this_week?: number;
    pending_approvals?: number;
    transcript_segments?: number;
  };
  attention_items?: DashboardAttentionItem[];
  recent_activity?: DashboardActivity[];
};

export type DashboardMeeting = {
  id: string;
  subject: string;
  start_time: string;
  end_time: string;
  bot_status?: string | null;
  approval_status?: string | null;
  organizer_email?: string | null;
};

export type DashboardTask = {
  id: string;
  title: string;
  description?: string | null;
  status: string;
  priority?: string | null;
  due_date?: string | null;
  meeting_id?: string | null;
  action_item_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type DashboardAttentionItem = {
  id: string;
  type: string;
  title: string;
  detail: string;
};

export type DashboardActivity = {
  id: string;
  type: string;
  message: string;
  created_at: string;
};

export type Meeting = {
  id: string;
  graph_event_id?: string;
  subject: string;
  organizer_email?: string | null;
  join_url?: string | null;
  start_time: string;
  end_time: string;
  status: string;
  bot_status: string;
  approval_status: string;
  source_type?: string | null;
  processing_status?: string | null;
  uploaded_media_url?: string | null;
  transcript_segment_count?: number;
  created_at?: string;
  updated_at?: string;
};

export type TranscriptSegment = {
  id: string;
  sequence?: number | null;
  speaker?: string | null;
  source_id?: string | null;
  language?: string | null;
  text: string;
  started_at?: string | null;
  ended_at?: string | null;
  created_at: string;
};

export type MeetingSummary = {
  id?: string;
  meeting_id?: string;
  summary: string;
  key_points: unknown[];
  decisions: unknown[];
  model?: string | null;
};

export type MeetingAIIntelligenceResult = {
  meeting_id: string;
  summary: MeetingSummary;
  generated_tasks_count: number;
  created_action_items_count: number;
  skipped_action_items_count: number;
  created_tasks_count: number;
  skipped_tasks_count: number;
  tasks: DashboardTask[];
};

export type MeetingChatSource = {
  id: string;
  chunk_text: string;
  speaker?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  source_segment_ids: string[];
};

export type MeetingChatMessage = {
  id: string;
  meeting_id: string;
  user_id: string;
  role: "user" | "assistant" | string;
  content: string;
  sources: MeetingChatSource[];
  created_at: string;
};

export type MeetingChatIndexStatus = {
  meeting_id: string;
  status: "not_indexed" | "indexing" | "ready" | "failed" | "empty" | string;
  indexed_chunk_count: number;
  transcript_segment_count: number;
  error_message?: string | null;
};

export type MeetingChatResult = {
  meeting_id: string;
  answer: string;
  sources: MeetingChatSource[];
};

export type ManualJoinPayload = {
  meeting_id?: string | null;
  join_web_url?: string | null;
  join_meeting_id?: string | null;
  passcode?: string | null;
  use_service_hosted_media: boolean;
};

export type ManualJoinResult = {
  status: string;
  meeting_id?: string | null;
  call_id?: string | null;
  state?: string | null;
  join_mode?: string | null;
  media_mode?: string | null;
  message: string;
};

export type UploadedRecordingJob = {
  id: string;
  meeting_id: string;
  user_id: string;
  status: string;
  original_filename: string;
  content_type?: string | null;
  transcript_segment_count: number;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type UploadedRecordingResult = {
  status: string;
  meeting: Meeting;
  job: UploadedRecordingJob;
};

export type TaskMeeting = {
  id: string;
  subject: string;
  start_time?: string | null;
  end_time?: string | null;
  organizer_email?: string | null;
};

export type BotHealth = {
  platform_api_configured: boolean;
  bot: {
    status: string;
    bot_instance_id?: string | null;
    version?: string | null;
    last_seen_at?: string | null;
    age_seconds?: number | null;
  };
  latest_event?: BotEvent | null;
  checks: Array<{
    name: string;
    status: string;
  }>;
};

export type BotEvent = {
  id: string;
  bot_instance_id: string;
  user_id?: string | null;
  meeting_id?: string | null;
  event_type: string;
  severity: string;
  message: string;
  payload?: Record<string, unknown>;
  created_at: string;
};

export type MeetingAssistantSettings = {
  user_id?: string | null;
  auto_join_enabled: boolean;
  require_approval: boolean;
  approval_lead_minutes: number;
  look_ahead_minutes: number;
  join_early_seconds: number;
  max_late_join_minutes: number;
  leave_grace_minutes: number;
  use_service_hosted_media: boolean;
};

export type UserBootstrapPayload = {
  email?: string | null;
  tenant_id?: string | null;
  aad_user_id?: string | null;
};

export type UserBootstrapResult = {
  user_id: string;
  calendar_connection_status: string;
};

export type TaskStatus = "todo" | "in_progress" | "blocked" | "done";
export type TaskPriority = "low" | "medium" | "high" | "urgent";

export type TaskAssignee = {
  user_id: string;
  display_name?: string | null;
  email?: string | null;
  role: "primary" | "collaborator" | string;
};

export type TaskItem = {
  id: string;
  organization_id?: string | null;
  owner_user_id: string;
  assignee_user_id?: string | null;
  meeting_id?: string | null;
  action_item_id?: string | null;
  title: string;
  description?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  assignees: TaskAssignee[];
  meeting?: TaskMeeting | null;
};

export type TaskPayload = {
  title: string;
  description?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date?: string | null;
  meeting_id?: string | null;
  action_item_id?: string | null;
  assignee_user_ids: string[];
};

export type ApprovalMeeting = {
  id: string;
  subject: string;
  start_time: string;
  end_time: string;
  bot_status?: string | null;
  approval_status?: string | null;
  organizer_email?: string | null;
};

export type ApprovalItem = {
  id: string;
  bot_approval_id?: string | null;
  meeting_id: string;
  user_id: string;
  status: "pending" | "approved" | "rejected" | "expired" | string;
  requested_via?: string | null;
  requested_at?: string | null;
  expires_at?: string | null;
  decided_at?: string | null;
  decided_by?: string | null;
  decided_via?: string | null;
  meeting?: ApprovalMeeting | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const accessToken =
    typeof window === "undefined"
      ? await getServerSupabaseAccessToken()
      : await getBrowserSupabaseAccessToken();

  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return fetch(input, {
    ...init,
    headers,
  });
}

async function getBrowserSupabaseAccessToken(): Promise<string | null> {
  const { supabaseBrowserClient } = await import("@/lib/supabase/client");
  const {
    data: { session },
  } = await supabaseBrowserClient.auth.getSession();
  return session?.access_token ?? null;
}

async function getServerSupabaseAccessToken(): Promise<string | null> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseAnonKey) {
    return null;
  }

  const [{ cookies }, { createServerClient }] = await Promise.all([
    import("next/headers"),
    import("@supabase/ssr"),
  ]);
  const cookieStore = await cookies();
  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll() {
        return;
      },
    },
  });
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

export async function getDashboard(): Promise<DashboardOverview> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/dashboard`, {
    next: { revalidate: 30 },
  });

  if (!response.ok) {
    throw new Error(`Dashboard request failed: ${response.status}`);
  }

  return response.json();
}

export async function getMeetingAssistantSettings(): Promise<MeetingAssistantSettings> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/settings/meeting-assistant`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Meeting assistant settings request failed: ${response.status}`);
  }

  return response.json();
}

export async function updateMeetingAssistantSettings(
  settings: MeetingAssistantSettings,
): Promise<MeetingAssistantSettings> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/settings/meeting-assistant`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  });

  if (!response.ok) {
    throw new Error(`Meeting assistant settings update failed: ${response.status}`);
  }

  return response.json();
}

export async function bootstrapUserWorkspace(
  payload: UserBootstrapPayload,
): Promise<UserBootstrapResult> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/onboarding/bootstrap`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `User bootstrap request failed: ${response.status}`);
  }

  return response.json();
}

export async function listMeetings(): Promise<Meeting[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Meetings request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.items ?? [];
}

export async function listTranscriptReadyMeetings(): Promise<Meeting[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings?transcript_ready=true`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Transcript-ready meetings request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.items ?? [];
}

export async function getMeeting(meetingId: string): Promise<Meeting> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/${meetingId}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Meeting request failed: ${response.status}`);
  }
  return response.json();
}

export async function getMeetingTranscript(meetingId: string): Promise<TranscriptSegment[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/${meetingId}/transcript`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Meeting transcript request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.segments ?? [];
}

export async function getMeetingSummary(meetingId: string): Promise<MeetingSummary> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/${meetingId}/summary`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Meeting summary request failed: ${response.status}`);
  }
  return response.json();
}

export async function getMeetingTasks(meetingId: string): Promise<DashboardTask[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/${meetingId}/tasks`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Meeting tasks request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.items ?? [];
}

export async function generateMeetingIntelligence(
  meetingId: string,
): Promise<MeetingAIIntelligenceResult> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/${meetingId}/ai-intelligence`, {
    method: "POST",
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Meeting AI request failed: ${response.status}`);
  }
  return response.json();
}

export async function uploadMeetingRecording(formData: FormData): Promise<UploadedRecordingResult> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/uploads`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Meeting upload failed: ${response.status}`);
  }

  return response.json();
}

export async function getMeetingChatMessages(meetingId: string): Promise<MeetingChatMessage[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/${meetingId}/chat/messages`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Meeting chat messages request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.items ?? [];
}

export async function getMeetingChatIndexStatus(
  meetingId: string,
): Promise<MeetingChatIndexStatus> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/meetings/${meetingId}/chat/index-status`,
    {
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error(`Meeting chat index status request failed: ${response.status}`);
  }
  return response.json();
}

export async function indexMeetingChat(meetingId: string): Promise<MeetingChatIndexStatus> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/${meetingId}/chat/index`, {
    method: "POST",
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Meeting chat index request failed: ${response.status}`);
  }
  return response.json();
}

export async function askMeetingChat(
  meetingId: string,
  message: string,
): Promise<MeetingChatResult> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/${meetingId}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Meeting chat request failed: ${response.status}`);
  }
  return response.json();
}

export async function manualJoinMeeting(payload: ManualJoinPayload): Promise<ManualJoinResult> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/meetings/manual-join`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Manual join failed: ${response.status}`);
  }
  return response.json();
}

export async function getBotHealth(): Promise<BotHealth> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/integrations/bot-health`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Bot health request failed: ${response.status}`);
  }
  return response.json();
}

export async function listBotEvents(): Promise<BotEvent[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/integrations/bot-events`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Bot events request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.items ?? [];
}

export async function listTasks(): Promise<TaskItem[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/tasks`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Tasks request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.items ?? [];
}

export async function createTask(payload: TaskPayload): Promise<TaskItem> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Task create request failed: ${response.status}`);
  }
  return response.json();
}

export async function updateTask(
  taskId: string,
  payload: Partial<TaskPayload>,
): Promise<TaskItem> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Task update request failed: ${response.status}`);
  }
  return response.json();
}

export async function deleteTask(taskId: string): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Task delete request failed: ${response.status}`);
  }
}

export async function listApprovals(): Promise<ApprovalItem[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/approvals`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Approvals request failed: ${response.status}`);
  }
  const data = await response.json();
  return data.items ?? [];
}

export async function decideApproval(
  approvalId: string,
  decision: "approve" | "reject",
): Promise<ApprovalItem> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/approvals/${approvalId}/${decision}`, {
    method: "POST",
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Approval decision failed: ${response.status}`);
  }
  return response.json();
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (data.detail) {
      return JSON.stringify(data.detail);
    }
  } catch {
    return null;
  }
  return null;
}
