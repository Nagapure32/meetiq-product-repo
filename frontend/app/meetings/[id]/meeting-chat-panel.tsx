"use client";

import { DatabaseZap, RefreshCw, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { EmptyBlock, StatusPill } from "@/components/ui";
import {
  askMeetingChat,
  getMeetingChatIndexStatus,
  getMeetingChatMessages,
  indexMeetingChat,
  type MeetingChatIndexStatus,
  type MeetingChatMessage,
  type MeetingChatSource,
} from "@/lib/api";
import { formatStatusLabel } from "@/lib/dashboard-ui";

type Props = {
  meetingId: string;
  transcriptCount: number;
};

export function MeetingChatPanel({ meetingId, transcriptCount }: Props) {
  const [messages, setMessages] = useState<MeetingChatMessage[]>([]);
  const [indexStatus, setIndexStatus] = useState<MeetingChatIndexStatus | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [indexing, setIndexing] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([getMeetingChatMessages(meetingId), getMeetingChatIndexStatus(meetingId)])
      .then(([loadedMessages, loadedStatus]) => {
        if (!active) {
          return;
        }
        setMessages(loadedMessages);
        setIndexStatus(loadedStatus);
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [meetingId]);

  const ready = indexStatus?.status === "ready";
  const empty = transcriptCount === 0 || indexStatus?.status === "empty";
  const canSend = ready && message.trim().length > 0 && !sending;
  const statusTone = useMemo(() => {
    if (ready) {
      return "good";
    }
    if (indexStatus?.status === "failed" || empty) {
      return "warn";
    }
    return "neutral";
  }, [empty, indexStatus?.status, ready]);

  async function handleIndex() {
    setIndexing(true);
    setError(null);
    try {
      const status = await indexMeetingChat(meetingId);
      setIndexStatus(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Indexing failed.");
    } finally {
      setIndexing(false);
    }
  }

  async function handleSend() {
    const question = message.trim();
    if (!question || !canSend) {
      return;
    }
    const userMessage: MeetingChatMessage = {
      id: `local-user-${Date.now()}`,
      meeting_id: meetingId,
      user_id: "local",
      role: "user",
      content: question,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((current) => [...current, userMessage]);
    setMessage("");
    setSending(true);
    setError(null);
    try {
      const result = await askMeetingChat(meetingId, question);
      setMessages((current) => [
        ...current,
        {
          id: `local-assistant-${Date.now()}`,
          meeting_id: meetingId,
          user_id: "local",
          role: "assistant",
          content: result.answer,
          sources: result.sources,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex min-h-[460px] flex-col">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill tone={statusTone}>{formatStatusLabel(indexStatus?.status ?? "loading")}</StatusPill>
          {indexStatus?.indexed_chunk_count ? (
            <StatusPill>{indexStatus.indexed_chunk_count} chunks</StatusPill>
          ) : null}
        </div>
        <button
          type="button"
          onClick={handleIndex}
          disabled={indexing || transcriptCount === 0}
          className="inline-flex h-9 items-center gap-2 rounded-[10px] border border-line bg-white px-3 text-xs font-medium text-ink disabled:cursor-not-allowed disabled:opacity-55"
        >
          {indexing ? <RefreshCw size={14} className="animate-spin" /> : <DatabaseZap size={14} />}
          {ready ? "Reindex" : "Prepare chat"}
        </button>
      </div>

      {error ? (
        <div className="mb-4 rounded-[10px] border border-[#f0dfb5] bg-[#fff5d8] p-3 text-xs leading-5 text-[#8a5d00]">
          {error}
        </div>
      ) : null}

      <div className="flex-1 space-y-4 overflow-auto pr-1">
        {loading ? (
          <EmptyBlock title="Loading chat" text="Meeting chat history and index status are loading." />
        ) : empty ? (
          <EmptyBlock title="Transcript required" text="AI chat becomes available after transcript lines are captured for this meeting." />
        ) : messages.length === 0 ? (
          <EmptyBlock title="No chat yet" text="Prepare this meeting, then ask a question about its transcript." />
        ) : (
          messages.map((item) => (
            <ChatBubble key={item.id} role={item.role} content={item.content} sources={item.sources} />
          ))
        )}
      </div>

      <div className="mt-5 border-t border-line pt-4">
        <div className="flex gap-3">
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void handleSend();
              }
            }}
            disabled={!ready || sending}
            className="h-10 flex-1 rounded-[10px] border border-[#cccbc6] bg-[#efefeb] px-4 text-xs outline-none disabled:cursor-not-allowed disabled:opacity-60"
            placeholder={ready ? "Ask about this meeting transcript..." : "Prepare chat before asking..."}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!canSend}
            className="grid h-10 w-12 place-items-center rounded-[10px] bg-brand text-white disabled:cursor-not-allowed disabled:opacity-55"
            aria-label="Send message"
          >
            <Send size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({
  role,
  content,
  sources,
}: {
  role: string;
  content: string;
  sources: MeetingChatSource[];
}) {
  const assistant = role === "assistant";
  return (
    <div className={`flex ${assistant ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[720px] rounded-[12px] border p-4 text-sm leading-6 ${
          assistant ? "border-line bg-white text-ink shadow-panel" : "border-brand bg-brand text-white"
        }`}
      >
        <p>{content}</p>
        {assistant && sources.length > 0 ? (
          <details className="mt-3 border-t border-line pt-3">
            <summary className="cursor-pointer text-[11px] font-medium text-muted">
              Evidence lines ({Math.min(sources.length, 3)})
            </summary>
            <div className="mt-2 space-y-2">
              {sources.slice(0, 3).map((source, index) => (
                <div key={`${source.id}-${index}`} className="text-[11px] leading-5 text-muted">
                  <span className="font-medium text-ink">
                    {source.speaker ?? "Unknown speaker"}
                    {source.started_at ? ` at ${formatTime(source.started_at)}` : ""}
                  </span>
                  <span> - {compactSourceText(source.chunk_text)}</span>
                </div>
              ))}
            </div>
          </details>
        ) : null}
      </div>
    </div>
  );
}

function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "--:--"
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function compactSourceText(value: string) {
  const text = value.replace(/\s+/g, " ").trim();
  if (text.length <= 180) {
    return text;
  }
  return `${text.slice(0, 177).trim()}...`;
}
