import { AppShell } from "@/components/app-shell";
import { PageHeader, Panel, StatusPill } from "@/components/ui";
import { MeetingAssistantSettingsForm } from "@/components/meeting-assistant-settings-form";
import { getMeetingAssistantSettings, type MeetingAssistantSettings } from "@/lib/api";

export const dynamic = "force-dynamic";

const fallbackSettings: MeetingAssistantSettings = {
  user_id: null,
  auto_join_enabled: false,
  require_approval: true,
  approval_lead_minutes: 2,
  look_ahead_minutes: 15,
  join_early_seconds: 0,
  max_late_join_minutes: 10,
  leave_grace_minutes: 2,
  use_service_hosted_media: false,
};

export default async function MeetingAssistantSettingsPage() {
  const settings = await getMeetingAssistantSettings().catch(() => fallbackSettings);

  return (
    <AppShell>
      <div className="h-full p-6">
        <PageHeader
          title="Meeting assistant settings"
          subtitle="Configure how the .NET Teams bot scans calendars, requests approval, and joins meetings."
        />
        <Panel
          title="Automation"
          className="mt-8"
          action={<StatusPill tone={settings.user_id ? "good" : "warn"}>{settings.user_id ? "Supabase" : "Fallback"}</StatusPill>}
        >
          <MeetingAssistantSettingsForm initialSettings={settings} />
        </Panel>
      </div>
    </AppShell>
  );
}
