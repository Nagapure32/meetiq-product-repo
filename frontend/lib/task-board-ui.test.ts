import {
  buildTaskSummary,
  filterTasks,
  formatCompactDate,
  isTaskOverdue,
} from "./task-board-ui.ts";
import type { TaskItem } from "./api";

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

const tasks: TaskItem[] = [
  {
    id: "task-1",
    owner_user_id: "user-1",
    title: "Send recap",
    status: "todo",
    priority: "urgent",
    due_date: "2026-05-28",
    assignees: [],
  },
  {
    id: "task-2",
    owner_user_id: "user-1",
    title: "Review blockers",
    status: "blocked",
    priority: "high",
    due_date: "2026-05-31",
    assignees: [],
  },
  {
    id: "task-3",
    owner_user_id: "user-1",
    title: "Done item",
    status: "done",
    priority: "low",
    due_date: "2026-05-20",
    assignees: [],
  },
];

const summary = buildTaskSummary(tasks, new Date("2026-05-29T12:00:00Z"));
assert(summary.total === 3, "Summary should count all tasks.");
assert(summary.open === 2, "Summary should count non-done tasks as open.");
assert(summary.blocked === 1, "Summary should count blocked tasks.");
assert(summary.done === 1, "Summary should count done tasks.");
assert(summary.overdue === 1, "Summary should count only open overdue tasks.");

const filtered = filterTasks(tasks, {
  query: "block",
  status: "all",
  priority: "all",
});
assert(filtered.length === 1 && filtered[0]?.id === "task-2", "Search should filter by title.");

assert(isTaskOverdue(tasks[0], new Date("2026-05-29T12:00:00Z")), "Open past-due task should be overdue.");
assert(!isTaskOverdue(tasks[2], new Date("2026-05-29T12:00:00Z")), "Done tasks should not be overdue.");
assert(formatCompactDate("2026-05-29").includes("May"), "Compact dates should be readable.");
