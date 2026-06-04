import { AppShell } from "@/components/app-shell";
import { ApprovalsBoard } from "@/components/approvals-board";
import { PageHeader } from "@/components/ui";
import { listApprovals } from "@/lib/api";

export default async function ApprovalsPage() {
  const approvalsResult = await listApprovals()
    .then((items) => ({ items, message: null }))
    .catch((error) => ({
      items: [],
      message: error instanceof Error ? error.message : "Approvals request failed.",
    }));

  return (
    <AppShell>
      <div className="h-full p-6">
        <PageHeader
          title="Approvals"
          subtitle="Review and decide pending bot join requests from Aress MeetIQ."
        />
        <ApprovalsBoard
          initialApprovals={approvalsResult.items}
          initialMessage={approvalsResult.message}
        />
      </div>
    </AppShell>
  );
}
