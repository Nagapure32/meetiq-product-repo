import { AppShell } from "@/components/app-shell";
import { PageHeader, Panel, StatusPill } from "@/components/ui";
import { getBotHealth, listBotEvents } from "@/lib/api";
import { formatStatusLabel, statusTone } from "@/lib/dashboard-ui";

export const dynamic = "force-dynamic";

export default async function IntegrationsPage() {
  const [health, events] = await Promise.all([
    getBotHealth().catch(() => null),
    listBotEvents().catch(() => []),
  ]);

  return (
    <AppShell>
      <div className="h-full p-6">
        <PageHeader
          title="Integrations"
          subtitle="Microsoft 365, Teams bot, Azure Speech, and transcript storage status."
        />
        <div className="mt-8 grid grid-cols-[1fr_360px] gap-5">
          <Panel title="Connection health">
            {(health?.checks ?? []).length === 0 ? (
              <>
                <IntegrationRow name="Supabase database" status="Unknown" />
                <IntegrationRow name="Teams bot heartbeat" status="No data" />
              </>
            ) : (
              health!.checks.map((check) => (
                <IntegrationRow
                  key={check.name}
                  name={check.name}
                  status={check.status}
                  ready={check.status === "connected" || check.status === "online" || check.status === "configured"}
                />
              ))
            )}
          </Panel>
          <Panel
            title="Teams bot"
            action={
              <StatusPill tone={statusTone(health?.bot.status ?? "unknown")}>
                {formatStatusLabel(health?.bot.status ?? "unknown")}
              </StatusPill>
            }
          >
            <div className="space-y-3 text-xs text-muted">
              <InfoRow label="Instance" value={health?.bot.bot_instance_id ?? "No heartbeat"} />
              <InfoRow label="Version" value={health?.bot.version ?? "Unknown"} />
              <InfoRow label="Last seen" value={health?.bot.last_seen_at ? formatDate(health.bot.last_seen_at) : "Never"} />
              <InfoRow label="Latest event" value={formatStatusLabel(health?.latest_event?.event_type ?? "No events")} />
            </div>
          </Panel>
        </div>

        <Panel title="Recent bot events" className="mt-5">
          {events.length === 0 ? (
            <div className="rounded-[12px] border border-dashed border-line bg-[#faf9f5] p-5 text-center">
              <p className="text-sm font-medium text-ink">No bot events yet</p>
              <p className="mt-1 text-xs text-muted">Start the .NET bot with FastAPI running to record heartbeats and events.</p>
            </div>
          ) : (
            <div className="divide-y divide-line">
              {events.map((event) => (
                <div key={event.id} className="grid grid-cols-[160px_1fr_auto] gap-4 py-3">
                  <div className="font-mono text-[11px] text-muted">{formatDate(event.created_at)}</div>
                  <div>
                    <p className="text-sm font-medium text-ink">{formatStatusLabel(event.event_type)}</p>
                    <p className="mt-1 text-xs text-muted">{event.message}</p>
                  </div>
                  <StatusPill tone={statusTone(event.severity)}>{formatStatusLabel(event.severity)}</StatusPill>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </AppShell>
  );
}

function IntegrationRow({ name, status, ready = false }: { name: string; status: string; ready?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-line py-3 last:border-b-0">
      <span className="text-sm font-medium text-ink">{name}</span>
      <StatusPill tone={ready ? "good" : "warn"}>{formatStatusLabel(status)}</StatusPill>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span>{label}</span>
      <span className="max-w-[190px] truncate text-right font-medium text-ink">{value}</span>
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown" : date.toLocaleString();
}
