import { Video } from "lucide-react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { UploadRecordingControl } from "@/components/upload-recording-control";
import { EmptyBlock, PageHeader, Panel, StatusPill } from "@/components/ui";
import { listMeetings } from "@/lib/api";
import { getCurrentMeetingStatus } from "@/lib/dashboard-ui";
import { ManualJoinControl } from "./manual-join-control";

export const dynamic = "force-dynamic";

export default async function MeetingsPage() {
  const meetings = await listMeetings().catch(() => []);
  const upcoming = meetings.filter((meeting) => new Date(meeting.end_time).getTime() >= Date.now());
  const recent = meetings.filter((meeting) => new Date(meeting.end_time).getTime() < Date.now());

  return (
    <AppShell>
      <div className="h-full p-6">
        <PageHeader
          title="Meetings"
          subtitle="Calendar meetings, bot join status, transcripts, and summaries."
          action={
            <div className="flex items-center gap-2">
              <UploadRecordingControl />
              <ManualJoinControl meetings={meetings} />
            </div>
          }
        />
        <div className="mt-8 grid grid-cols-[1fr_320px] gap-5">
          <Panel title="Upcoming meetings">
            {upcoming.length === 0 ? (
              <EmptyBlock
                title="No meetings synced yet"
                text={
                  "After Microsoft calendar is connected, upcoming Teams meetings will appear " +
                  "here with their current status."
                }
              />
            ) : (
              <MeetingList meetings={upcoming} />
            )}
          </Panel>
          <Panel title="Meeting assistant">
            <div className="space-y-3 text-xs text-muted">
              <div className="flex items-center justify-between">
                <span>Auto-join</span>
                <StatusPill tone="good">Enabled</StatusPill>
              </div>
              <div className="flex items-center justify-between">
                <span>Approval required</span>
                <StatusPill tone="brand">On</StatusPill>
              </div>
              <div className="flex items-center justify-between">
                <span>Calendar users</span>
                <StatusPill>{meetings.length} synced</StatusPill>
              </div>
            </div>
          </Panel>
        </div>
        <Panel title="Recent meetings" className="mt-5">
          {recent.length === 0 ? (
            <div
              className={[
                "flex items-center gap-3 rounded-[12px] border border-line",
                "bg-[#faf9f5] p-4",
              ].join(" ")}
            >
              <div
                className={[
                  "grid size-9 place-items-center rounded-[10px]",
                  "bg-brand-soft text-brand-dark",
                ].join(" ")}
              >
                <Video size={16} />
              </div>
              <div>
                <p className="text-sm font-medium text-ink">Waiting for completed meetings</p>
                <p className="mt-1 text-xs text-muted">
                  Recent meetings will appear after the bot reports meeting events to FastAPI.
                </p>
              </div>
            </div>
          ) : (
            <MeetingList meetings={recent} />
          )}
        </Panel>
      </div>
    </AppShell>
  );
}

function MeetingList({ meetings }: { meetings: Awaited<ReturnType<typeof listMeetings>> }) {
  return (
    <div className="divide-y divide-line">
      {meetings.map((meeting) => {
        const currentStatus = getCurrentMeetingStatus(meeting);
        return (
          <Link
            href={`/meetings/${meeting.id}`}
            key={meeting.id}
            className="grid grid-cols-[120px_1fr_auto] items-center gap-4 py-4"
          >
            <div className="font-mono text-[11px] text-muted">
              <p>{formatDate(meeting.start_time)}</p>
              <p>{formatTime(meeting.start_time)}-{formatTime(meeting.end_time)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-ink">{meeting.subject}</p>
              <p className="mt-1 text-xs text-muted">
                {meeting.organizer_email ?? "Organizer unavailable"}
              </p>
            </div>
            <div className="flex gap-2">
              <StatusPill tone={currentStatus.tone}>{currentStatus.label}</StatusPill>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown" : date.toLocaleDateString();
}

function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "--:--"
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
