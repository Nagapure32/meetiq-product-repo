import { FileText } from "lucide-react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { EmptyBlock, PageHeader, Panel, StatusPill } from "@/components/ui";
import { listTranscriptReadyMeetings } from "@/lib/api";
import { getCurrentMeetingStatus } from "@/lib/dashboard-ui";

export const dynamic = "force-dynamic";

export default async function TranscriptsPage() {
  const meetings = await listTranscriptReadyMeetings().catch(() => []);
  const completedMeetings = meetings.filter(
    (meeting) => new Date(meeting.end_time).getTime() < Date.now(),
  );

  return (
    <AppShell>
      <div className="h-full p-6">
        <PageHeader
          title="Transcripts"
          subtitle="Browse meeting transcripts by meeting, then open the full transcript, summary, and linked tasks."
        />

        <Panel title="Meeting transcript library" className="mt-8">
          {completedMeetings.length === 0 ? (
            <EmptyBlock
              title="No completed meeting transcripts yet"
              text="Completed meetings with synced transcript lines will appear here after the bot posts them to FastAPI."
            />
          ) : (
            <div className="divide-y divide-line">
              {completedMeetings.map((meeting) => {
                const currentStatus = getCurrentMeetingStatus(meeting);
                return (
                  <Link
                    href={`/meetings/${meeting.id}`}
                    key={meeting.id}
                    className="grid grid-cols-[44px_1fr_auto] items-center gap-4 py-4"
                  >
                    <div className="grid size-10 place-items-center rounded-[10px] bg-brand-soft text-brand-dark">
                      <FileText size={16} />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink">{meeting.subject}</p>
                      <p className="mt-1 text-xs text-muted">
                        {formatDateTime(meeting.start_time)} -{" "}
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
          )}
        </Panel>
      </div>
    </AppShell>
  );
}

function formatDateTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Unknown time"
    : date.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}
