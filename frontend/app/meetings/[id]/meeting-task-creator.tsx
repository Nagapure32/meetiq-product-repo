"use client";

import { Check, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createTask, type TaskPriority } from "@/lib/api";
import { formatStatusLabel } from "@/lib/dashboard-ui";
import type { MeetingTaskPrefill } from "@/lib/meeting-task-prefill";

const priorities: TaskPriority[] = ["low", "medium", "high", "urgent"];

type Props = {
  meetingId: string;
  prefill: MeetingTaskPrefill;
};

export function MeetingTaskCreator({ meetingId, prefill }: Props) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [title, setTitle] = useState(prefill.title);
  const [description, setDescription] = useState(prefill.description);
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [dueDate, setDueDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function saveTask() {
    const normalizedTitle = title.trim();
    if (!normalizedTitle) {
      setError("Task title is required.");
      return;
    }

    setSaving(true);
    setError(null);
    setSaved(false);

    try {
      await createTask({
        title: normalizedTitle,
        description: description.trim() || null,
        status: "todo",
        priority,
        due_date: dueDate || null,
        meeting_id: meetingId,
        action_item_id: null,
        assignee_user_ids: [],
      });
      setSaved(true);
      setExpanded(false);
      router.refresh();
    } catch (taskError) {
      setError(taskError instanceof Error ? taskError.message : "Task create failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mb-4 rounded-[12px] border border-line bg-[#faf9f5] p-3">
      <button
        className="flex h-9 w-full items-center justify-center gap-2 rounded-[10px] bg-brand px-3 text-xs font-medium text-white disabled:opacity-60"
        onClick={() => {
          setExpanded((current) => !current);
          setSaved(false);
        }}
        disabled={saving}
      >
        {saved ? <Check size={13} /> : <Plus size={13} />}
        {saved ? "Task created" : expanded ? "Close task form" : "Create task from meeting"}
      </button>

      {expanded ? (
        <div className="mt-4 space-y-3">
          <label className="block">
            <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
              Title
            </span>
            <input
              className="input-control mt-2"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>

          <label className="block">
            <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
              Description
            </span>
            <textarea
              className="input-control mt-2 min-h-[120px] resize-none py-3"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
                Priority
              </span>
              <select
                className="input-control mt-2"
                value={priority}
                onChange={(event) => setPriority(event.target.value as TaskPriority)}
              >
                {priorities.map((item) => (
                  <option key={item} value={item}>
                    {formatStatusLabel(item)}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
                Due date
              </span>
              <input
                className="input-control mt-2"
                type="date"
                value={dueDate}
                onChange={(event) => setDueDate(event.target.value)}
              />
            </label>
          </div>

          {error ? (
            <p className="rounded-[10px] bg-[#fff5d8] p-3 text-xs text-[#8a5d00]">{error}</p>
          ) : null}

          <button
            className="flex h-9 w-full items-center justify-center gap-2 rounded-[10px] bg-brand px-3 text-xs font-medium text-white disabled:opacity-60"
            onClick={saveTask}
            disabled={saving}
          >
            <Plus size={13} />
            {saving ? "Saving task" : "Save linked task"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
