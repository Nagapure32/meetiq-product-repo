import { AppShell } from "@/components/app-shell";
import { PageHeader, Panel, StatusPill } from "@/components/ui";

const languages = ["en-IN", "en-US", "hi-IN", "mr-IN"];

export default function TranscriptionSettingsPage() {
  return (
    <AppShell>
      <div className="h-full p-6">
        <PageHeader
          title="Transcription settings"
          subtitle="Control Azure Speech language detection and candidate languages."
        />
        <Panel title="Language detection" className="mt-8">
          <div className="flex items-center justify-between border-b border-line pb-4">
            <span className="text-sm font-medium text-ink">Auto-detect languages</span>
            <StatusPill tone="good">Enabled</StatusPill>
          </div>
          <div className="mt-5">
            <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted">Candidate languages</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {languages.map((language) => (
                <StatusPill key={language} tone="brand">
                  {language}
                </StatusPill>
              ))}
            </div>
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}

