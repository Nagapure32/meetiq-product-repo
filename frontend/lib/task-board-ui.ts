import type { TaskItem, TaskPriority, TaskStatus } from "@/lib/api";

export type TaskFilterValue<T extends string> = T | "all";

export type TaskFilters = {
  query: string;
  status: TaskFilterValue<TaskStatus>;
  priority: TaskFilterValue<TaskPriority>;
};

export type TaskSummary = {
  total: number;
  open: number;
  blocked: number;
  done: number;
  overdue: number;
};

export function buildTaskSummary(tasks: TaskItem[], now = new Date()): TaskSummary {
  return tasks.reduce(
    (summary, task) => {
      summary.total += 1;
      if (task.status === "done") {
        summary.done += 1;
      } else {
        summary.open += 1;
      }
      if (task.status === "blocked") {
        summary.blocked += 1;
      }
      if (isTaskOverdue(task, now)) {
        summary.overdue += 1;
      }
      return summary;
    },
    { total: 0, open: 0, blocked: 0, done: 0, overdue: 0 },
  );
}

export function filterTasks(tasks: TaskItem[], filters: TaskFilters): TaskItem[] {
  const query = filters.query.trim().toLowerCase();
  return tasks.filter((task) => {
    if (filters.status !== "all" && task.status !== filters.status) {
      return false;
    }
    if (filters.priority !== "all" && task.priority !== filters.priority) {
      return false;
    }
    if (!query) {
      return true;
    }
    return [
      task.title,
      task.description,
      task.meeting?.subject,
      task.meeting?.organizer_email,
      ...task.assignees.map((assignee) => assignee.display_name ?? assignee.email ?? assignee.user_id),
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
  });
}

export function isTaskOverdue(task: TaskItem, now = new Date()): boolean {
  if (task.status === "done" || !task.due_date) {
    return false;
  }
  const dueDate = parseDateOnly(task.due_date);
  if (!dueDate) {
    return false;
  }
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return dueDate.getTime() < today.getTime();
}

export function formatCompactDate(value?: string | null): string {
  if (!value) {
    return "No due date";
  }
  const date = parseDateOnly(value) ?? new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }
  return date.toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
}

function parseDateOnly(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) {
    return null;
  }
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}
