"use client";

import { Bot, FileText } from "lucide-react";
import { useState } from "react";
import { EmptyBlock, Panel, StatusPill } from "@/components/ui";
import type { TranscriptSegment } from "@/lib/api";
import { MeetingChatPanel } from "./meeting-chat-panel";

export function MeetingTranscriptTabs({
  meetingId,
  segments,
}: {
  meetingId: string;
  segments: TranscriptSegment[];
}) {
  const [mode, setMode] = useState<"transcript" | "chat">("transcript");

  return (
    <Panel
      title={mode === "transcript" ? "Transcript" : "AI chat"}
      className="flex h-full min-h-0 flex-col"
      action={
        <div className="grid grid-cols-2 rounded-[10px] border border-line bg-[#efefeb] p-1">
          <button
            type="button"
            onClick={() => setMode("transcript")}
            className={`inline-flex h-8 items-center justify-center gap-2 rounded-[8px] px-3 text-xs ${
              mode === "transcript" ? "bg-white font-medium text-ink shadow-panel" : "text-muted"
            }`}
          >
            <FileText size={13} />
            Transcript
          </button>
          <button
            type="button"
            onClick={() => setMode("chat")}
            className={`inline-flex h-8 items-center justify-center gap-2 rounded-[8px] px-3 text-xs ${
              mode === "chat" ? "bg-white font-medium text-ink shadow-panel" : "text-muted"
            }`}
          >
            <Bot size={13} />
            AI Chat
          </button>
        </div>
      }
    >
      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        {mode === "chat" ? (
          <MeetingChatPanel meetingId={meetingId} transcriptCount={segments.length} />
        ) : (
          <TranscriptList segments={segments} />
        )}
      </div>
    </Panel>
  );
}

function TranscriptList({ segments }: { segments: TranscriptSegment[] }) {
  if (segments.length === 0) {
    return (
      <EmptyBlock
        title="No transcript synced yet"
        text="Finalized transcript lines will appear here after the bot posts them to FastAPI. Azure Blob remains the archive store."
      />
    );
  }

  return (
    <div className="space-y-4">
      {segments.map((segment) => (
        <div key={segment.id} className="rounded-[12px] border border-line bg-[#faf9f5] p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-ink">
                {segment.speaker ?? "Unknown speaker"}
              </span>
              {segment.language ? <StatusPill tone="brand">{segment.language}</StatusPill> : null}
            </div>
            <span className="font-mono text-[10px] text-muted">
              {formatTime(segment.started_at ?? segment.created_at)}
            </span>
          </div>
          <p className="text-sm leading-6 text-ink">{segment.text}</p>
          {segment.source_id ? (
            <p className="mt-2 font-mono text-[10px] text-muted">source {segment.source_id}</p>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "--:--"
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
