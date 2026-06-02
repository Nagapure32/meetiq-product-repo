import {
  AlertTriangle,
  ArrowRight,
  Bot,
  CalendarDays,
  CheckCircle2,
  Clock,
  Video,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { StatusPill } from "@/components/ui";
import { UploadRecordingControl } from "@/components/upload-recording-control";
import { DashboardOverview, getDashboard, listTasks, type TaskItem } from "@/lib/api";
import { DashboardGreeting } from "./dashboard-greeting";
import {
  buildDashboardSearchItems,
  filterDashboardAttentionItems,
  formatStatusLabel,
  getAttentionTasks,
  getCurrentMeetingStatus,
  statusTone,
} from "@/lib/dashboard-ui";

export const dynamic = "force-dynamic";

const fallbackDashboard: DashboardOverview = {
  metrics: [
    { label: "Meetings today", value: 0, helper: "API offline" },
    { label: "Open follow-ups", value: 0, helper: "API offline" },
    { label: "Overdue", value: 0, helper: "API offline" },
    { label: "Completion rate", value: "0%", helper: "API offline" },
  ],
  upcoming_meetings: [],
  recent_action_items: [],
  bot_status: {
    status: "api_offline",
    message: "Start the FastAPI backend to load live platform data.",
  },
  task_summary: {
    open: 0,
    completed: 0,
    overdue: 0,
    created_today: 0,
    completion_rate: 0,
  },
  attention_items: [],
  recent_activity: [],
};

const fallbackTaskSummary = {
  open: 0,
  completed: 0,
  overdue: 0,
  created_today: 0,
  completion_rate: 0,
};

export default async function DashboardPage() {
  const [dashboard, tasks, userName] = await Promise.all([
    getDashboard().catch(() => fallbackDashboard),
    listTasks().catch(() => [] as TaskItem[]),
    getLoggedInUserName(),
  ]);
  const attentionItems = filterDashboardAttentionItems(dashboard.attention_items);
  const attentionTasks = getAttentionTasks(tasks);
  const recentActivity = dashboard.recent_activity ?? [];
  const taskSummary = dashboard.task_summary ?? fallbackTaskSummary;
  const searchItems = buildDashboardSearchItems(dashboard, tasks);
  const hasLiveData = dashboard.bot_status.status !== "api_offline";

  return (
    <AppShell searchItems={searchItems}>
      <div className="mx-auto w-full max-w-[1440px] p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <DashboardGreeting userName={userName} />
            <p className="mt-1 text-[13px] text-muted">
              {taskSummary.open} open follow-ups, {taskSummary.overdue} overdue,{" "}
              {dashboard.upcoming_meetings.length} meetings ahead.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <UploadRecordingControl />
            <Link
              href="/meetings"
              className="flex h-8 items-center gap-2 rounded-md bg-brand px-4 text-xs font-medium text-white"
            >
              <Video size={13} />
              Meetings
            </Link>
          </div>
        </div>

        <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {dashboard.metrics.map((metric) => (
            <MetricCard key={metric.label} metric={metric} />
          ))}
        </section>

        <section className="mt-5 grid items-stretch gap-5 xl:grid-cols-[1fr_380px]">
          <div className="space-y-5">
            <PanelShell
              title="Today's meetings"
              action={
                <Link href="/meetings" className="text-[11px] font-medium text-brand-dark">
                  View all
                </Link>
              }
            >
              {dashboard.upcoming_meetings.length === 0 ? (
                <EmptyState
                  icon={<CalendarDays size={18} />}
                  title="No meetings synced yet"
                  text="Connect Microsoft calendar and enable the assistant to fill your day view."
                />
              ) : (
                <div className="space-y-3">
                  {dashboard.upcoming_meetings.map((meeting) => {
                    const currentStatus = getCurrentMeetingStatus(meeting);
                    return (
                      <div
                        key={meeting.id}
                        className="grid gap-3 border-b border-line py-3 last:border-b-0 md:grid-cols-[96px_1fr_auto]"
                      >
                        <div className="font-mono text-[11px] text-muted">
                          <p>{formatTime(meeting.start_time)}</p>
                          <p>{formatTime(meeting.end_time)}</p>
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-ink">{meeting.subject}</p>
                          <p className="mt-1 text-xs text-muted">
                            {meeting.organizer_email ?? "Organizer unavailable"}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center justify-end gap-2">
                          <StatusPill tone={currentStatus.tone}>{currentStatus.label}</StatusPill>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </PanelShell>

            <PanelShell
              title="Recent activity"
              action={<ActivityPill status={dashboard.bot_status.status} />}
              className="h-[420px] flex flex-col"
              bodyClassName="min-h-0 flex-1 overflow-y-auto pr-1"
            >
              {recentActivity.length === 0 ? (
                <EmptyState
                  icon={<Bot size={18} />}
                  title="No assistant activity yet"
                  text="When meetings are detected or processed, recent updates will appear here."
                />
              ) : (
                <div className="space-y-3">
                  {recentActivity.map((activity) => (
                    <div
                      key={`${activity.type}-${activity.id}`}
                      className="flex items-start gap-3 rounded-lg border border-line bg-[#faf9f5] p-3"
                    >
                      <div className="grid size-8 shrink-0 place-items-center rounded-md bg-brand-soft text-brand-dark">
                        <Bot size={15} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-ink">{activity.message}</p>
                        <p className="mt-1 font-mono text-[10px] uppercase text-muted">
                          {formatDateTime(activity.created_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </PanelShell>
          </div>
          <div className="min-h-0 xl:h-full">
            <PanelShell
              title="Today needs attention"
              action={<StatusPill tone={attentionTasks.length || attentionItems.length ? "warn" : "good"}>{attentionTasks.length + attentionItems.length}</StatusPill>}
              className="flex flex-col xl:h-full"
              bodyClassName="min-h-0 flex-1 overflow-y-auto pr-1"
            >
              {!hasLiveData ? (
                <EmptyState
                  icon={<AlertTriangle size={18} />}
                  title="Can't check attention items"
                  text={dashboard.bot_status.message}
                />
              ) : attentionTasks.length === 0 && attentionItems.length === 0 ? (
                <EmptyState
                  icon={<CheckCircle2 size={18} />}
                  title="Nothing urgent"
                  text="No overdue follow-ups or pending approval items are waiting right now."
                />
              ) : (
                <div className="space-y-3">
                  {attentionTasks.map((task) => (
                    <AttentionTaskCard key={task.id} task={task} />
                  ))}
                  {attentionItems.map((item) => (
                    <Link
                      key={`${item.type}-${item.id}`}
                      href={item.type === "approval" ? "/approvals" : "/tasks"}
                      className="block rounded-lg border border-line p-3 transition hover:border-brand hover:bg-[#faf9f5]"
                    >
                      <div className="flex items-start gap-2">
                        <AlertTriangle size={15} className="mt-0.5 shrink-0 text-[#8a5d00]" />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-ink">{item.title}</p>
                          <p className="mt-1 text-xs text-muted">{item.detail}</p>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </PanelShell>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

async function getLoggedInUserName() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseAnonKey) {
    return "Calendar user";
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
  const user = session?.user;
  const metadata = user?.user_metadata ?? {};
  return (
    asString(metadata.full_name) ??
    asString(metadata.name) ??
    asString(metadata.preferred_username) ??
    user?.email ??
    "Calendar user"
  );
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function MetricCard({
  metric,
}: {
  metric: { label: string; value: number | string; helper?: string | null };
}) {
  return (
    <div className="rounded-lg border border-line bg-white p-[18px] shadow-panel">
      <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
        {metric.label}
      </p>
      <p className="mt-3 text-[28px] font-semibold text-ink">{metric.value}</p>
      <p className={`mt-2 font-mono text-[11px] ${metricHelperClass(metric)}`}>{metric.helper ?? "Ready"}</p>
    </div>
  );
}

function PanelShell({
  title,
  action,
  children,
  className = "",
  bodyClassName = "",
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={`rounded-lg border border-line bg-white p-5 shadow-panel ${className}`}>
      <div className="mb-5 flex items-center justify-between gap-3">
        <h2 className="text-[13px] font-semibold text-ink">{title}</h2>
        {action}
      </div>
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

function ActivityPill({ status }: { status: string }) {
  return <StatusPill tone={statusTone(status)}>{formatStatusLabel(status)}</StatusPill>;
}

function EmptyState({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-[#faf9f5] p-5 text-center">
      <div className="mx-auto grid size-9 place-items-center rounded-md bg-brand-soft text-brand-dark">
        {icon}
      </div>
      <p className="mt-3 text-sm font-medium text-ink">{title}</p>
      <p className="mx-auto mt-1 max-w-[360px] text-xs leading-5 text-muted">{text}</p>
    </div>
  );
}

function AttentionTaskCard({ task }: { task: TaskItem }) {
  const assignees = task.assignees.length
    ? task.assignees.map((assignee) => assignee.display_name ?? assignee.email ?? shortId(assignee.user_id)).join(", ")
    : "Unassigned";

  return (
    <article
      tabIndex={0}
      className="group rounded-lg border border-line bg-white p-3 outline-none transition hover:border-brand hover:bg-[#faf9f5] focus:border-brand focus:bg-[#faf9f5]"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-ink">{task.title}</p>
          <p className="mt-1 flex items-center gap-1 text-[11px] text-muted">
            <Clock size={12} /> {task.due_date ? `Due ${task.due_date}` : "No due date"}
          </p>
        </div>
        <StatusPill tone={statusTone(task.priority)}>{formatStatusLabel(task.priority)}</StatusPill>
      </div>

      <div className="mt-3 hidden rounded-[10px] border border-line bg-white p-3 text-xs group-hover:block group-focus:block">
        {task.description ? <p className="leading-5 text-ink">{task.description}</p> : null}
        <div className="mt-3 space-y-2 text-[11px] text-muted">
          <DetailRow label="Status" value={formatStatusLabel(task.status)} />
          <DetailRow label="Assigned to" value={assignees} />
          {task.meeting ? (
            <>
              <DetailRow label="Meeting" value={task.meeting.subject} />
              <DetailRow label="Organizer" value={task.meeting.organizer_email ?? "Organizer unavailable"} />
            </>
          ) : task.meeting_id ? (
            <DetailRow label="Meeting" value={shortId(task.meeting_id)} />
          ) : null}
        </div>
        <Link
          href="/tasks"
          className="mt-3 inline-flex h-8 items-center justify-center gap-1 rounded-[9px] bg-brand px-3 text-[11px] font-medium text-white"
        >
          Open task <ArrowRight size={12} />
        </Link>
      </div>
    </article>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="w-20 shrink-0 font-medium text-ink">{label}</span>
      <span className="min-w-0 flex-1">{value}</span>
    </div>
  );
}

function metricHelperClass(metric: { label: string; helper?: string | null }) {
  const value = `${metric.label} ${metric.helper ?? ""}`.toLowerCase();
  if (value.includes("offline") || value.includes("overdue") || value.includes("attention")) {
    return "text-[#8a5d00]";
  }
  if (value.includes("done") || value.includes("completion")) {
    return "text-[#2a7a4b]";
  }
  return "text-muted";
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--:--";
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Time unavailable";
  }

  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortId(value: string) {
  return value.length > 8 ? value.slice(0, 8) : value;
}

