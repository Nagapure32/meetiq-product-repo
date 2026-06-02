import { AppShell } from "@/components/app-shell";
import { PageHeader, StatusPill } from "@/components/ui";
import { listTranscriptReadyMeetings } from "@/lib/api";
import { AiChatWorkspace } from "./ai-chat-workspace";

export const dynamic = "force-dynamic";

export default async function AiChatPage() {
  const meetings = await listTranscriptReadyMeetings().catch(() => []);
  return (
    <AppShell>
      <div className="flex h-full flex-col p-6">
        <PageHeader
          title="AI Chat"
          subtitle="Select one meeting and chat with only that meeting's transcript."
          action={<StatusPill tone="brand">meeting scoped</StatusPill>}
        />
        <AiChatWorkspace meetings={meetings} />
      </div>
    </AppShell>
  );
}
