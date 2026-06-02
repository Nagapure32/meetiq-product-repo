"use client";

import {
  CalendarDays,
  CheckCircle2,
  Circle,
  Clock3,
  ExternalLink,
  Filter,
  Search,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";

import { Panel, StatusPill } from "@/components/ui";
import {
  deleteTask,
  type TaskAssignee,
  type TaskItem,
  type TaskPriority,
  type TaskStatus,
  updateTask,
} from "@/lib/api";
import {
  buildTaskSummary,
  filterTasks,
  formatCompactDate,
  isTaskOverdue,
  type TaskFilterValue,
} from "@/lib/task-board-ui";

const statuses: Array<{ label: string; value: TaskStatus }> = [
  { label: "Backlog", value: "todo" },
  { label: "In progress", value: "in_progress" },
  { label: "Blocked", value: "blocked" },
  { label: "Done", value: "done" },
];

const priorities: Array<{ label: string; value: TaskPriority }> = [
  { label: "Urgent", value: "urgent" },
  { label: "High", value: "high" },
  { label: "Medium", value: "medium" },
  { label: "Low", value: "low" },
];

export function TaskBoard({ initialTasks }: { initialTasks: TaskItem[] }) {
  const [tasks, setTasks] = useState(initialTasks);
  const [selectedTaskId, setSelectedTaskId] = useState(initialTasks[0]?.id ?? "");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<TaskFilterValue<TaskStatus>>("all");
  const [priorityFilter, setPriorityFilter] = useState<TaskFilterValue<TaskPriority>>("all");
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const summary = useMemo(() => buildTaskSummary(tasks), [tasks]);
  const filteredTasks = useMemo(
    () => filterTasks(tasks, { query, status: statusFilter, priority: priorityFilter }),
    [priorityFilter, query, statusFilter, tasks],
  );
  const selectedTask =
    tasks.find((task) => task.id === selectedTaskId) ?? filteredTasks[0] ?? tasks[0] ?? null;

  async function changeStatus(task: TaskItem, status: TaskStatus) {
    if (task.status === status || pendingTaskId) {
      return;
    }
    const previousTasks = tasks;
    setPendingTaskId(task.id);
    setError(null);
    setTasks((current) => current.map((item) => (item.id === task.id ? { ...item, status } : item)));
    try {
      const updated = await updateTask(task.id, { status });
      setTasks((current) => current.map((item) => (item.id === task.id ? updated : item)));
    } catch (taskError) {
      setTasks(previousTasks);
      setError(taskError instanceof Error ? taskError.message : "Status update failed.");
    } finally {
      setPendingTaskId(null);
    }
  }

  async function removeTask(taskId: string) {
    if (pendingTaskId) {
      return;
    }
    const previousTasks = tasks;
    setPendingTaskId(taskId);
    setError(null);
    setTasks((current) => current.filter((task) => task.id !== taskId));
    if (selectedTaskId === taskId) {
      const nextTask = tasks.find((task) => task.id !== taskId);
      setSelectedTaskId(nextTask?.id ?? "");
    }
    try {
      await deleteTask(taskId);
    } catch (taskError) {
      setTasks(previousTasks);
      setError(taskError instanceof Error ? taskError.message : "Task delete failed.");
    } finally {
      setPendingTaskId(null);
    }
  }

  return (
    <div className="mt-8 space-y-4">
      <SummaryStrip summary={summary} />

      {error ? (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-[#f0dfb5] bg-[#fff5d8] px-3 py-2 text-xs text-[#8a5d00]">
          <span>{error}</span>
          <button type="button" className="font-medium text-ink" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Panel
          title="Tasks"
          action={<StatusPill>{filteredTasks.length} shown</StatusPill>}
          className="min-h-[560px]"
        >
          <TaskToolbar
            query={query}
            statusFilter={statusFilter}
            priorityFilter={priorityFilter}
            onQueryChange={setQuery}
            onStatusFilterChange={setStatusFilter}
            onPriorityFilterChange={setPriorityFilter}
          />

          <div className="mt-4 overflow-x-auto rounded-lg border border-line">
            <div className="grid min-w-[780px] grid-cols-[minmax(260px,1.4fr)_120px_110px_100px_150px_40px] gap-3 border-b border-line bg-[#faf9f5] px-3 py-2 font-mono text-[10px] uppercase tracking-[0.06em] text-muted">
              <span>Task</span>
              <span>Status</span>
              <span>Priority</span>
              <span>Due</span>
              <span>Owner</span>
              <span />
            </div>

            <div className="max-h-[520px] min-w-[780px] overflow-y-auto">
              {filteredTasks.length === 0 ? (
                <div className="p-8 text-center">
                  <p className="text-sm font-medium text-ink">No matching tasks</p>
                  <p className="mt-1 text-xs text-muted">Adjust the filters or search term.</p>
                </div>
              ) : (
                filteredTasks.map((task) => (
                  <TaskRow
                    key={task.id}
                    task={task}
                    selected={selectedTask?.id === task.id}
                    pending={pendingTaskId === task.id}
                    onSelect={() => setSelectedTaskId(task.id)}
                    onDelete={() => removeTask(task.id)}
                  />
                ))
              )}
            </div>
          </div>
        </Panel>

        <TaskDetailPanel
          task={selectedTask}
          pending={selectedTask ? pendingTaskId === selectedTask.id : false}
          onStatusChange={(status) => selectedTask && changeStatus(selectedTask, status)}
          onDelete={() => selectedTask && removeTask(selectedTask.id)}
        />
      </div>
    </div>
  );
}

function SummaryStrip({ summary }: { summary: ReturnType<typeof buildTaskSummary> }) {
  const items = [
    { label: "Total", value: summary.total, tone: "neutral" as const, icon: Circle },
    { label: "Open", value: summary.open, tone: "brand" as const, icon: Clock3 },
    { label: "Blocked", value: summary.blocked, tone: "warn" as const, icon: Filter },
    { label: "Done", value: summary.done, tone: "good" as const, icon: CheckCircle2 },
    { label: "Overdue", value: summary.overdue, tone: "warn" as const, icon: CalendarDays },
  ];

  return (
    <section className="grid gap-3 md:grid-cols-5">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <div key={item.label} className="rounded-lg border border-line bg-white px-4 py-3 shadow-panel">
            <div className="flex items-center justify-between gap-2">
              <p className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted">{item.label}</p>
              <StatusPill tone={item.tone}>
                <Icon size={10} />
              </StatusPill>
            </div>
            <p className="mt-2 text-xl font-semibold text-ink">{item.value}</p>
          </div>
        );
      })}
    </section>
  );
}

function TaskToolbar({
  query,
  statusFilter,
  priorityFilter,
  onQueryChange,
  onStatusFilterChange,
  onPriorityFilterChange,
}: {
  query: string;
  statusFilter: TaskFilterValue<TaskStatus>;
  priorityFilter: TaskFilterValue<TaskPriority>;
  onQueryChange: (value: string) => void;
  onStatusFilterChange: (value: TaskFilterValue<TaskStatus>) => void;
  onPriorityFilterChange: (value: TaskFilterValue<TaskPriority>) => void;
}) {
  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(220px,1fr)_160px_160px]">
      <label className="flex h-9 items-center gap-2 rounded-md border border-line bg-[#faf9f5] px-3 text-xs text-muted focus-within:border-brand focus-within:bg-white">
        <Search size={14} />
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          className="h-full min-w-0 flex-1 bg-transparent text-xs text-ink outline-none placeholder:text-muted"
          placeholder="Search tasks, meetings, owners"
        />
      </label>
      <select
        className="h-9 rounded-md border border-line bg-white px-3 text-xs text-ink outline-none"
        value={statusFilter}
        onChange={(event) => onStatusFilterChange(event.target.value as TaskFilterValue<TaskStatus>)}
      >
        <option value="all">All statuses</option>
        {statuses.map((status) => (
          <option key={status.value} value={status.value}>
            {status.label}
          </option>
        ))}
      </select>
      <select
        className="h-9 rounded-md border border-line bg-white px-3 text-xs text-ink outline-none"
        value={priorityFilter}
        onChange={(event) => onPriorityFilterChange(event.target.value as TaskFilterValue<TaskPriority>)}
      >
        <option value="all">All priorities</option>
        {priorities.map((priority) => (
          <option key={priority.value} value={priority.value}>
            {priority.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function TaskRow({
  task,
  selected,
  pending,
  onSelect,
  onDelete,
}: {
  task: TaskItem;
  selected: boolean;
  pending: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const owner = primaryAssignee(task.assignees);
  const overdue = isTaskOverdue(task);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      className={`grid w-full min-w-[780px] grid-cols-[minmax(260px,1.4fr)_120px_110px_100px_150px_40px] items-center gap-3 border-b border-line px-3 py-3 text-left last:border-b-0 ${
        selected ? "bg-brand-soft" : "bg-white hover:bg-[#faf9f5]"
      }`}
    >
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium text-ink">{task.title}</span>
        <span className="mt-1 block truncate text-[11px] text-muted">
          {task.meeting?.subject ?? task.description ?? "No meeting linked"}
        </span>
      </span>
      <StatusPill tone={statusTone(task.status)}>{statusLabel(task.status)}</StatusPill>
      <StatusPill tone={priorityTone(task.priority)}>{priorityLabel(task.priority)}</StatusPill>
      <span className={`text-xs ${overdue ? "font-medium text-[#8a5d00]" : "text-muted"}`}>
        {formatCompactDate(task.due_date)}
      </span>
      <span className="truncate text-xs text-ink">{owner}</span>
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          onDelete();
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            event.stopPropagation();
            onDelete();
          }
        }}
        aria-label={`Delete ${task.title}`}
        className={`grid size-8 place-items-center rounded-md border border-line bg-white text-muted ${
          pending ? "pointer-events-none opacity-50" : "hover:border-[#f0dfb5] hover:text-[#8a5d00]"
        }`}
      >
        <Trash2 size={13} />
      </button>
    </div>
  );
}

function TaskDetailPanel({
  task,
  pending,
  onStatusChange,
  onDelete,
}: {
  task: TaskItem | null;
  pending: boolean;
  onStatusChange: (status: TaskStatus) => void;
  onDelete: () => void;
}) {
  if (!task) {
    return (
      <Panel title="Task details" className="min-h-[560px]">
        <div className="rounded-lg border border-dashed border-line bg-[#faf9f5] p-5 text-center">
          <p className="text-sm font-medium text-ink">No task selected</p>
          <p className="mt-1 text-xs text-muted">Select a task to review details and update status.</p>
        </div>
      </Panel>
    );
  }

  return (
    <Panel title="Task details" className="min-h-[560px]">
      <div className="space-y-5">
        <div>
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-base font-semibold leading-6 text-ink">{task.title}</h2>
            <StatusPill tone={priorityTone(task.priority)}>{priorityLabel(task.priority)}</StatusPill>
          </div>
          <p className="mt-3 text-xs leading-5 text-muted">
            {task.description || "No description added for this task."}
          </p>
        </div>

        <div className="grid gap-3 text-xs">
          <DetailRow label="Status">
            <select
              className="h-9 w-full rounded-md border border-line bg-white px-3 text-xs text-ink outline-none"
              value={task.status}
              onChange={(event) => onStatusChange(event.target.value as TaskStatus)}
              disabled={pending}
            >
              {statuses.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </DetailRow>
          <DetailRow label="Due date">
            <span className={isTaskOverdue(task) ? "font-medium text-[#8a5d00]" : "text-ink"}>
              {formatCompactDate(task.due_date)}
            </span>
          </DetailRow>
          <DetailRow label="Assignees">
            <AssigneeList assignees={task.assignees} />
          </DetailRow>
          <DetailRow label="Action item">
            <span className="font-mono text-[11px] text-muted">
              {task.action_item_id ? shortId(task.action_item_id) : "None"}
            </span>
          </DetailRow>
        </div>

        {task.meeting ? (
          <Link
            href={`/meetings/${task.meeting.id}`}
            className="flex items-start gap-3 rounded-lg border border-line bg-[#faf9f5] p-3 text-xs text-ink transition hover:border-brand hover:bg-white"
          >
            <CalendarDays size={15} className="mt-0.5 shrink-0 text-brand-dark" />
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium">{task.meeting.subject}</span>
              <span className="mt-1 block text-[11px] text-muted">
                {formatMeetingDate(task.meeting.start_time)} - {task.meeting.organizer_email ?? "Organizer unavailable"}
              </span>
            </span>
            <ExternalLink size={13} className="mt-0.5 shrink-0 text-muted" />
          </Link>
        ) : null}

        <button
          type="button"
          className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-md border border-line bg-white text-xs font-medium text-muted transition hover:border-[#f0dfb5] hover:text-[#8a5d00] disabled:opacity-50"
          onClick={onDelete}
          disabled={pending}
        >
          <Trash2 size={13} />
          Delete task
        </button>
      </div>
    </Panel>
  );
}

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[88px_minmax(0,1fr)] items-center gap-3">
      <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted">{label}</span>
      <span className="min-w-0">{children}</span>
    </div>
  );
}

function AssigneeList({ assignees }: { assignees: TaskAssignee[] }) {
  if (!assignees.length) {
    return <span className="text-muted">Unassigned</span>;
  }
  return (
    <span className="flex flex-wrap gap-1.5">
      {assignees.map((assignee) => (
        <span
          key={assignee.user_id}
          title={assignee.email ?? assignee.user_id}
          className="rounded-full border border-line bg-white px-2 py-1 text-[10px] font-medium text-ink"
        >
          {assignee.display_name ?? assignee.email ?? shortId(assignee.user_id)}
        </span>
      ))}
    </span>
  );
}

function primaryAssignee(assignees: TaskAssignee[]): string {
  const primary = assignees.find((assignee) => assignee.role === "primary") ?? assignees[0];
  return primary?.display_name ?? primary?.email ?? (primary ? shortId(primary.user_id) : "Unassigned");
}

function statusTone(status: TaskStatus): "neutral" | "good" | "warn" | "brand" {
  if (status === "done") {
    return "good";
  }
  if (status === "blocked") {
    return "warn";
  }
  if (status === "in_progress") {
    return "brand";
  }
  return "neutral";
}

function priorityTone(priority: TaskPriority): "neutral" | "good" | "warn" | "brand" {
  if (priority === "urgent" || priority === "high") {
    return "warn";
  }
  if (priority === "low") {
    return "good";
  }
  return "neutral";
}

function statusLabel(status: TaskStatus): string {
  return statuses.find((item) => item.value === status)?.label ?? status;
}

function priorityLabel(priority: TaskPriority): string {
  return priorities.find((item) => item.value === priority)?.label ?? priority;
}

function shortId(value: string) {
  return value.length > 8 ? value.slice(0, 8) : value;
}

function formatMeetingDate(value?: string | null) {
  if (!value) {
    return "Meeting time unavailable";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Meeting time unavailable"
    : date.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}
