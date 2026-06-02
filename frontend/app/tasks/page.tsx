import { AppShell } from "@/components/app-shell";
import { TaskBoard } from "@/components/task-board";
import { PageHeader } from "@/components/ui";
import { listTasks } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TasksPage() {
  const tasks = await listTasks().catch(() => []);

  return (
    <AppShell>
      <div className="h-full p-6">
        <PageHeader
          title="Task board"
          subtitle="Create, assign, and track tasks from meetings or manual follow-up work."
        />
        <TaskBoard initialTasks={tasks} />
      </div>
    </AppShell>
  );
}
