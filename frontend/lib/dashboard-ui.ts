import type { DashboardOverview, TaskItem } from "@/lib/api";

export type SearchItem = {
  id: string;
  label: string;
  description: string;
  href: string;
  category: "Navigation" | "Meeting" | "Task" | "Attention" | "Activity";
};

export type StatusTone = "neutral" | "good" | "warn" | "brand";

export type CurrentMeetingStatusInput = {
  status?: string | null;
  bot_status?: string | null;
  approval_status?: string | null;
};

export type CurrentMeetingStatus = {
  value: string;
  label: string;
  tone: StatusTone;
};

const warningStatuses = new Set([
  "api_offline",
  "offline",
  "stale",
  "failed",
  "error",
  "pending",
  "blocked",
  "overdue",
  "urgent",
  "high",
  "rejected",
  "expired",
  "need attention",
  "not_connected",
]);

const goodStatuses = new Set(["online", "ready", "approved", "done", "completed", "success"]);
const brandStatuses = new Set(["joining", "recording", "processing", "in_progress"]);
const activeBotStatuses = new Set(["joining", "recording", "processing", "in_progress"]);
const inactiveBotStatuses = new Set(["not_started", "idle", "none"]);
const terminalApprovalStatuses = new Set(["rejected", "expired"]);

export function buildDashboardSearchItems(
  dashboard: DashboardOverview,
  tasks: TaskItem[] = [],
): SearchItem[] {
  const meetingItems = dashboard.upcoming_meetings.map((meeting) => ({
    id: `meeting-${meeting.id}`,
    label: meeting.subject || "Untitled meeting",
    description: meeting.organizer_email ?? "Meeting",
    href: `/meetings/${meeting.id}`,
    category: "Meeting" as const,
  }));

  const taskItems = tasks.map((task) => ({
    id: `task-${task.id}`,
    label: task.title || "Untitled task",
    description: [formatStatusLabel(task.status), formatStatusLabel(task.priority)]
      .filter(Boolean)
      .join(" - "),
    href: "/tasks",
    category: "Task" as const,
  }));

  const attentionItems = (dashboard.attention_items ?? []).map((item) => ({
    id: `attention-${item.type}-${item.id}`,
    label: item.title,
    description: item.detail,
    href: item.type === "approval" ? "/approvals" : "/tasks",
    category: "Attention" as const,
  }));

  const activityItems = (dashboard.recent_activity ?? []).map((item) => ({
    id: `activity-${item.type}-${item.id}`,
    label: item.message,
    description: formatStatusLabel(item.type),
    href: "/integrations",
    category: "Activity" as const,
  }));

  return [...meetingItems, ...taskItems, ...attentionItems, ...activityItems];
}

export function getAttentionTasks(tasks: TaskItem[], now = new Date()): TaskItem[] {
  const today = startOfDay(now).getTime();
  return tasks
    .filter((task) => {
      if (task.status === "done" || !task.due_date) {
        return false;
      }
      const dueDate = new Date(task.due_date);
      return !Number.isNaN(dueDate.getTime()) && startOfDay(dueDate).getTime() < today;
    })
    .sort((first, second) => priorityWeight(second.priority) - priorityWeight(first.priority));
}

export function filterDashboardAttentionItems(
  items: DashboardOverview["attention_items"] = [],
): NonNullable<DashboardOverview["attention_items"]> {
  return items.filter((item) => item.type !== "task");
}

export function formatStatusLabel(value?: string | null): string {
  if (!value) {
    return "Unknown";
  }
  const words = value
    .replace(/[_-]+/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => titleCaseWord(part));
  return words.join(" ");
}

export function statusTone(value?: string | null): StatusTone {
  const normalized = value?.toLowerCase() ?? "";
  if (warningStatuses.has(normalized)) {
    return "warn";
  }
  if (goodStatuses.has(normalized)) {
    return "good";
  }
  if (brandStatuses.has(normalized)) {
    return "brand";
  }
  return "neutral";
}

export function getCurrentMeetingStatus(meeting: CurrentMeetingStatusInput): CurrentMeetingStatus {
  const approvalStatus = normalizeStatus(meeting.approval_status);
  if (approvalStatus === "pending") {
    return buildCurrentMeetingStatus("pending", "Approval Pending");
  }
  if (terminalApprovalStatuses.has(approvalStatus)) {
    return buildCurrentMeetingStatus(approvalStatus, `Approval ${formatStatusLabel(approvalStatus)}`);
  }

  const botStatus = normalizeStatus(meeting.bot_status);
  if (activeBotStatuses.has(botStatus)) {
    return buildCurrentMeetingStatus(botStatus);
  }
  if (warningStatuses.has(botStatus) && !inactiveBotStatuses.has(botStatus)) {
    return buildCurrentMeetingStatus(botStatus, `Bot ${formatStatusLabel(botStatus)}`);
  }

  const meetingStatus = normalizeStatus(meeting.status);
  if (meetingStatus) {
    return buildCurrentMeetingStatus(meetingStatus);
  }
  if (botStatus) {
    return buildCurrentMeetingStatus(botStatus);
  }

  return buildCurrentMeetingStatus("unknown", "Unknown");
}

export function priorityWeight(value?: string | null): number {
  if (value === "urgent") {
    return 4;
  }
  if (value === "high") {
    return 3;
  }
  if (value === "medium") {
    return 2;
  }
  if (value === "low") {
    return 1;
  }
  return 0;
}

export function getTimeGreeting(hour: number): string {
  if (hour < 12) {
    return "Good morning";
  }
  if (hour < 17) {
    return "Good afternoon";
  }
  return "Good evening";
}

function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function normalizeStatus(value?: string | null): string {
  return value?.trim().toLowerCase() ?? "";
}

function buildCurrentMeetingStatus(value: string, label = formatStatusLabel(value)): CurrentMeetingStatus {
  return {
    value,
    label,
    tone: statusTone(value),
  };
}

function titleCaseWord(value: string): string {
  const normalized = value.toLowerCase();
  if (normalized === "api") {
    return "API";
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}
