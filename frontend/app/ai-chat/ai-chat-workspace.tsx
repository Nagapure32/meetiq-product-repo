"use client";

import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { EmptyBlock, Panel, StatusPill } from "@/components/ui";
import type { Meeting } from "@/lib/api";
import { getCurrentMeetingStatus } from "@/lib/dashboard-ui";
import { MeetingChatPanel } from "@/app/meetings/[id]/meeting-chat-panel";

export function AiChatWorkspace({ meetings }: { meetings: Meeting[] }) {
  const [query, setQuery] = useState("");
  const [selectedMeetingId, setSelectedMeetingId] = useState(meetings[0]?.id ?? "");

  const filteredMeetings = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return meetings;
    }
    return meetings.filter((meeting) =>
      [meeting.subject, meeting.organizer_email, meeting.start_time]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(normalized),
    );
  }, [meetings, query]);
  const selectedMeeting = meetings.find((meeting) => meeting.id === selectedMeetingId) ?? null;

  return (
    <div className="mt-8 grid min-h-[560px] grid-cols-[320px_1fr] gap-5">
      <Panel title="Meetings">
        <div className="mb-4 flex h-10 items-center gap-2 rounded-[10px] border border-line bg-[#efefeb] px-3">
          <Search size={14} className="text-muted" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-xs outline-none"
            placeholder="Search meetings..."
          />
        </div>
        <div className="space-y-2">
          {filteredMeetings.length === 0 ? (
            <EmptyBlock
              title={meetings.length === 0 ? "No meetings with transcripts yet" : "No meetings found"}
              text={
                meetings.length === 0
                  ? "Meetings appear here after transcript lines are captured."
                  : "Try another title, organizer, or date."
              }
            />
          ) : (
            filteredMeetings.map((meeting) => {
              const currentStatus = getCurrentMeetingStatus(meeting);
              return (
                <button
                  key={meeting.id}
                  type="button"
                  onClick={() => setSelectedMeetingId(meeting.id)}
                  className={`w-full rounded-[10px] border p-3 text-left ${
                    selectedMeetingId === meeting.id
                      ? "border-brand bg-brand-soft"
                      : "border-line bg-[#faf9f5]"
                  }`}
                >
                  <p className="text-xs font-semibold leading-5 text-ink">{meeting.subject}</p>
                  <p className="mt-1 text-[11px] leading-4 text-muted">
                    {formatDateTime(meeting.start_time)}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <StatusPill tone={currentStatus.tone}>{currentStatus.label}</StatusPill>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </Panel>

      <Panel
        title={selectedMeeting ? selectedMeeting.subject : "Select a meeting"}
        action={selectedMeeting ? <StatusPill tone="brand">meeting scoped</StatusPill> : null}
      >
        {selectedMeeting ? (
          <MeetingChatPanel
            meetingId={selectedMeeting.id}
            transcriptCount={selectedMeeting.transcript_segment_count ?? 0}
          />
        ) : (
          <EmptyBlock
            title={meetings.length === 0 ? "No meetings with transcripts yet" : "Choose a meeting"}
            text={
              meetings.length === 0
                ? "AI chat becomes available after transcript lines are captured for a meeting."
                : "Select a meeting from the list to chat with only that meeting's transcript."
            }
          />
        )}
      </Panel>
    </div>
  );
}

function formatDateTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown time" : date.toLocaleString();
}
