"use client";

import { Bot, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { generateMeetingIntelligence } from "@/lib/api";

export function MeetingAIActions({
  meetingId,
  hasSummary,
  linkedTaskCount,
}: {
  meetingId: string;
  hasSummary: boolean;
  linkedTaskCount: number;
}) {
  const router = useRouter();
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAI() {
    setRunning(true);
    setMessage(null);
    setError(null);

    try {
      const result = await generateMeetingIntelligence(meetingId);
      setMessage(formatResultMessage(result.created_tasks_count, result.skipped_tasks_count));
      router.refresh();
    } catch (meetingError) {
      setError(meetingError instanceof Error ? meetingError.message : "AI task creation failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mb-4 rounded-[12px] border border-line bg-[#faf9f5] p-3">
      <button
        className="flex h-9 w-full items-center justify-center gap-2 rounded-[10px] bg-ink px-3 text-xs font-medium text-white disabled:opacity-60"
        onClick={runAI}
        disabled={running}
      >
        {running ? <Bot size={13} /> : <Sparkles size={13} />}
        {running ? "Finding meeting tasks" : "Generate AI tasks"}
      </button>
      {message ? <p className="mt-3 text-xs leading-5 text-muted">{message}</p> : null}
      {!message && !error ? (
        <p className="mt-3 text-xs leading-5 text-muted">
          {hasSummary ? "AI summary exists" : "No AI summary yet"} · {linkedTaskCount} linked task
          {linkedTaskCount === 1 ? "" : "s"}
        </p>
      ) : null}
      {error ? (
        <p className="mt-3 rounded-[10px] bg-[#fff5d8] p-3 text-xs text-[#8a5d00]">{error}</p>
      ) : null}
    </div>
  );
}

function formatResultMessage(createdTasks: number, skippedTasks: number) {
  if (createdTasks === 0 && skippedTasks > 0) {
    return `No new tasks created. ${skippedTasks} existing task${
      skippedTasks === 1 ? " was" : "s were"
    } already found.`;
  }
  if (skippedTasks > 0) {
    return `Created ${createdTasks} new task${
      createdTasks === 1 ? "" : "s"
    }. Skipped ${skippedTasks} existing task${skippedTasks === 1 ? "" : "s"}.`;
  }
  return `Created ${createdTasks} task${createdTasks === 1 ? "" : "s"} from this meeting.`;
}
