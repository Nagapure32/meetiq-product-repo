import { Activity, BarChart3, Bot, CheckCircle2, Clock3, ListTodo } from "lucide-react";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { PageHeader, Panel, StatusPill } from "@/components/ui";
import { DashboardOverview, getDashboard } from "@/lib/api";
import { formatStatusLabel, statusTone } from "@/lib/dashboard-ui";

export const dynamic = "force-dynamic";

const fallbackDashboard: DashboardOverview = {
  metrics: [],
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
    weekly_meeting_hours: 0,
    meetings_this_week: 0,
    pending_approvals: 0,
    transcript_segments: 0,
  },
  attention_items: [],
  recent_activity: [],
};

export default async function InsightsPage() {
  const dashboard = await getDashboard().catch(() => fallbackDashboard);
  const summary = dashboard.task_summary ?? fallbackDashboard.task_summary!;
  const recentActivity = dashboard.recent_activity ?? [];
  const completionRate = summary.completion_rate ?? 0;
  const meetingsThisWeek = summary.meetings_this_week ?? 0;
  const weeklyMeetingHours = summary.weekly_meeting_hours ?? 0;
  const pendingApprovals = summary.pending_approvals ?? 0;
  const transcriptSegments = summary.transcript_segments ?? 0;

  return (
    <AppShell>
      <div className="h-full p-6">
        <PageHeader
          title="Insights"
          subtitle="A weekly view of how Aress MeetIQ is helping you stay on top of meetings and follow-ups."
        />

        <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <InsightMetric
            icon={<Clock3 size={16} />}
            label="Meeting hours"
            value={weeklyMeetingHours}
            helper={`${meetingsThisWeek} meetings this week`}
          />
          <InsightMetric
            icon={<ListTodo size={16} />}
            label="Open follow-ups"
            value={summary.open}
            helper={`${summary.created_today} created today`}
          />
          <InsightMetric
            icon={<CheckCircle2 size={16} />}
            label="Completion rate"
            value={`${completionRate}%`}
            helper={`${summary.completed} completed`}
          />
          <InsightMetric
            icon={<Bot size={16} />}
            label="Assistant status"
            value={formatStatusLabel(dashboard.bot_status.status)}
            helper={dashboard.bot_status.message}
          />
        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-[1fr_360px]">
          <Panel title="Weekly progress">
            <div className="space-y-5">
              <ProgressRow
                label="Follow-up completion"
                value={completionRate}
                detail={`${summary.completed} done, ${summary.open} still open`}
              />
              <ProgressRow
                label="Transcript coverage"
                value={transcriptSegments > 0 ? 100 : 0}
                detail={`${transcriptSegments} transcript segments synced`}
              />
              <ProgressRow
                label="Approval load"
                value={pendingApprovals > 0 ? 40 : 100}
                detail={
                  pendingApprovals > 0
                    ? `${pendingApprovals} pending approval decisions`
                    : "No pending approval decisions"
                }
              />
            </div>
          </Panel>

          <Panel title="This week at a glance">
            <div className="space-y-3">
              <GlanceItem
                icon={<BarChart3 size={15} />}
                label="Meeting load"
                value={`${weeklyMeetingHours} hours`}
              />
              <GlanceItem
                icon={<ListTodo size={15} />}
                label="Follow-ups created today"
                value={String(summary.created_today)}
              />
              <GlanceItem
                icon={<CheckCircle2 size={15} />}
                label="Completed follow-ups"
                value={String(summary.completed)}
              />
              <GlanceItem
                icon={<Activity size={15} />}
                label="Overdue"
                value={String(summary.overdue)}
              />
            </div>
          </Panel>
        </section>

        <Panel
          title="Recent assistant activity"
          className="mt-5"
          action={
            <StatusPill tone={statusTone(dashboard.bot_status.status)}>
              {formatStatusLabel(dashboard.bot_status.status)}
            </StatusPill>
          }
        >
          {recentActivity.length === 0 ? (
            <div className="rounded-lg border border-dashed border-line bg-[#faf9f5] p-5 text-center">
              <p className="text-sm font-medium text-ink">No activity yet</p>
              <p className="mx-auto mt-1 max-w-[420px] text-xs leading-5 text-muted">
                Meeting detection, joining, transcription, and summary updates will appear here.
              </p>
            </div>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {recentActivity.map((activity) => (
                <div
                  key={`${activity.type}-${activity.id}`}
                  className="rounded-lg border border-line bg-[#faf9f5] p-3"
                >
                  <p className="text-xs font-medium text-ink">{activity.message}</p>
                  <p className="mt-2 font-mono text-[10px] uppercase text-muted">
                    {activity.type} · {formatDateTime(activity.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </AppShell>
  );
}

function InsightMetric({
  icon,
  label,
  value,
  helper,
}: {
  icon: ReactNode;
  label: string;
  value: number | string;
  helper: string;
}) {
  return (
    <Panel>
      <div className="flex items-center gap-2 text-muted">
        <span className="grid size-7 place-items-center rounded-md bg-brand-soft text-brand-dark">
          {icon}
        </span>
        <p className="text-[11px] font-medium uppercase tracking-[0.06em]">{label}</p>
      </div>
      <p className="mt-4 text-[28px] font-semibold text-ink">{value}</p>
      <p className="mt-2 text-xs leading-5 text-muted">{helper}</p>
    </Panel>
  );
}

function ProgressRow({ label, value, detail }: { label: string; value: number; detail: string }) {
  const safeValue = Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium text-ink">{label}</p>
        <p className="font-mono text-[11px] text-muted">{safeValue}%</p>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#efefeb]">
        <div className="h-full rounded-full bg-brand" style={{ width: `${safeValue}%` }} />
      </div>
      <p className="mt-2 text-xs text-muted">{detail}</p>
    </div>
  );
}

function GlanceItem({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-line bg-[#faf9f5] p-3">
      <div className="flex min-w-0 items-center gap-2">
        <span className="grid size-7 shrink-0 place-items-center rounded-md bg-white text-brand-dark">
          {icon}
        </span>
        <p className="truncate text-xs font-medium text-ink">{label}</p>
      </div>
      <p className="font-mono text-[11px] text-muted">{value}</p>
    </div>
  );
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "time unavailable";
  }

  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
