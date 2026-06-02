import {
  buildDashboardSearchItems,
  filterDashboardAttentionItems,
  formatStatusLabel,
  getAttentionTasks,
  getCurrentMeetingStatus,
  getTimeGreeting,
  statusTone,
} from "./dashboard-ui.ts";
import type { DashboardOverview, TaskItem } from "./api";

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

const dashboard: DashboardOverview = {
  metrics: [],
  upcoming_meetings: [
    {
      id: "meeting-1",
      subject: "Roadmap sync",
      start_time: "2026-05-28T10:00:00Z",
      end_time: "2026-05-28T10:30:00Z",
      bot_status: "not_started",
      approval_status: "pending",
      organizer_email: "pm@example.com",
    },
  ],
  recent_action_items: [],
  bot_status: {
    status: "api_offline",
    message: "Start the backend.",
  },
  attention_items: [
    {
      id: "approval-1",
      type: "approval",
      title: "Meeting approval waiting",
      detail: "Review the pending bot join request.",
    },
  ],
  recent_activity: [
    {
      id: "activity-1",
      type: "bot",
      message: "Bot joined Standup.",
      created_at: "2026-05-28T09:00:00Z",
    },
  ],
};

const tasks: TaskItem[] = [
  {
    id: "task-1",
    owner_user_id: "user-1",
    title: "Send launch recap",
    description: "Include blockers and owners.",
    status: "todo",
    priority: "urgent",
    due_date: "2026-05-27",
    assignees: [{ user_id: "user-2", display_name: "Asha", email: "asha@example.com", role: "primary" }],
    meeting: {
      id: "meeting-1",
      subject: "Roadmap sync",
      start_time: "2026-05-28T10:00:00Z",
      organizer_email: "pm@example.com",
    },
  },
  {
    id: "task-2",
    owner_user_id: "user-1",
    title: "Already closed",
    status: "done",
    priority: "low",
    due_date: "2026-05-20",
    assignees: [],
  },
];

const searchItems = buildDashboardSearchItems(dashboard, tasks);
assert(
  searchItems.some((item) => item.label === "Roadmap sync" && item.href === "/meetings/meeting-1"),
  "Search should include dashboard meetings with direct meeting links.",
);
assert(
  searchItems.some((item) => item.label === "Send launch recap" && item.href === "/tasks"),
  "Search should include task items with task route links.",
);
assert(formatStatusLabel("not_started") === "Not started", "Snake-case statuses should become readable labels.");
assert(formatStatusLabel("in_progress") === "In Progress", "Multi-word statuses should be title cased.");
assert(formatStatusLabel("api_offline") === "API Offline", "Snake-case statuses should title case every word.");
assert(formatStatusLabel("online") === "Online", "Single-word lowercase statuses should be capitalized.");
assert(formatStatusLabel("no data") === "No Data", "Spaced lowercase labels should title case every word.");
assert(getTimeGreeting(9) === "Good morning", "Morning hours should show Good morning.");
assert(getTimeGreeting(14) === "Good afternoon", "Afternoon hours should show Good afternoon.");
assert(getTimeGreeting(20) === "Good evening", "Evening hours should show Good evening.");
assert(statusTone("api_offline") === "warn", "Offline bot status should use warning tone.");
assert(statusTone("approved") === "good", "Approved status should use good tone.");
assert(
  getCurrentMeetingStatus({
    status: "scheduled",
    bot_status: "not_started",
    approval_status: "pending",
  }).label === "Approval Pending",
  "Pending approval should be the current meeting status.",
);
assert(
  getCurrentMeetingStatus({
    status: "scheduled",
    bot_status: "recording",
    approval_status: "approved",
  }).label === "Recording",
  "Active bot status should be shown after approval is resolved.",
);
assert(
  getCurrentMeetingStatus({
    status: "completed",
    bot_status: "not_started",
    approval_status: "approved",
  }).label === "Completed",
  "Meeting status should be the fallback when approval and bot state are not active.",
);

const attentionTasks = getAttentionTasks(tasks, new Date("2026-05-28T12:00:00Z"));
assert(attentionTasks.length === 1, "Only open overdue tasks should be attention tasks.");
assert(attentionTasks[0]?.priority === "urgent", "Attention tasks should preserve priority.");

const filteredAttentionItems = filterDashboardAttentionItems([
  {
    id: "task-1",
    type: "task",
    title: "Send launch recap",
    detail: "Due 2026-05-27",
  },
  {
    id: "approval-1",
    type: "approval",
    title: "Meeting approval waiting",
    detail: "Review the pending bot join request.",
  },
]);
assert(filteredAttentionItems.length === 1, "Backend task attention items should not duplicate task cards.");
assert(filteredAttentionItems[0]?.type === "approval", "Non-task attention items should remain visible.");
