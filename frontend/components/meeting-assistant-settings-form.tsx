"use client";

import { Save } from "lucide-react";
import { useState, useTransition } from "react";
import {
  type MeetingAssistantSettings,
  updateMeetingAssistantSettings,
} from "@/lib/api";
import { StatusPill } from "@/components/ui";

type Props = {
  initialSettings: MeetingAssistantSettings;
};

export function MeetingAssistantSettingsForm({ initialSettings }: Props) {
  const [settings, setSettings] = useState(initialSettings);
  const [savedSettings, setSavedSettings] = useState(initialSettings);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const dirty = JSON.stringify(settings) !== JSON.stringify(savedSettings);

  function update<K extends keyof MeetingAssistantSettings>(
    key: K,
    value: MeetingAssistantSettings[K],
  ) {
    setSettings((current) => ({ ...current, [key]: value }));
    setMessage(null);
  }

  function save() {
    startTransition(async () => {
      try {
        const updated = await updateMeetingAssistantSettings(settings);
        setSettings(updated);
        setSavedSettings(updated);
        setMessage("Settings saved.");
      } catch {
        setMessage("Could not save settings. Check that FastAPI is running.");
      }
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between rounded-[12px] border border-line bg-[#faf9f5] p-4">
        <div>
          <p className="text-sm font-medium text-ink">Current source</p>
          <p className="mt-1 text-xs text-muted">
            {settings.user_id ? `Supabase user ${settings.user_id}` : "Local fallback values"}
          </p>
        </div>
        <StatusPill tone={settings.user_id ? "good" : "warn"}>
          {settings.user_id ? "Connected" : "Fallback"}
        </StatusPill>
      </div>

      <div className="divide-y divide-line">
        <ToggleRow
          label="Enable auto-join"
          description="Allow the bot to scan this user's calendar and join eligible meetings."
          value={settings.auto_join_enabled}
          onChange={(value) => update("auto_join_enabled", value)}
        />
        <ToggleRow
          label="Require approval"
          description="Ask for approval before the bot joins a meeting."
          value={settings.require_approval}
          onChange={(value) => update("require_approval", value)}
        />
        <NumberRow
          label="Approval lead time"
          suffix="minutes"
          value={settings.approval_lead_minutes}
          min={0}
          onChange={(value) => update("approval_lead_minutes", value)}
        />
        <NumberRow
          label="Look ahead window"
          suffix="minutes"
          value={settings.look_ahead_minutes}
          min={1}
          onChange={(value) => update("look_ahead_minutes", value)}
        />
        <NumberRow
          label="Join early"
          suffix="seconds"
          value={settings.join_early_seconds}
          min={0}
          onChange={(value) => update("join_early_seconds", value)}
        />
        <NumberRow
          label="Max late join"
          suffix="minutes"
          value={settings.max_late_join_minutes}
          min={0}
          onChange={(value) => update("max_late_join_minutes", value)}
        />
        <NumberRow
          label="Leave grace"
          suffix="minutes"
          value={settings.leave_grace_minutes}
          min={0}
          onChange={(value) => update("leave_grace_minutes", value)}
        />
        <ToggleRow
          label="Use service-hosted media"
          description="Use Graph service-hosted media instead of application-hosted media when supported."
          value={settings.use_service_hosted_media}
          onChange={(value) => update("use_service_hosted_media", value)}
        />
      </div>

      <div className="flex items-center justify-between border-t border-line pt-5">
        <p className="text-xs text-muted">{message ?? (dirty ? "Unsaved changes" : "No unsaved changes")}</p>
        <button
          type="button"
          onClick={save}
          disabled={!dirty || isPending}
          className="flex h-9 items-center gap-2 rounded-[10px] bg-brand px-4 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Save size={14} />
          {isPending ? "Saving..." : "Save settings"}
        </button>
      </div>
    </div>
  );
}

function ToggleRow({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description: string;
  value: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-6 py-4">
      <div>
        <p className="text-sm font-medium text-ink">{label}</p>
        <p className="mt-1 text-xs leading-5 text-muted">{description}</p>
      </div>
      <button
        type="button"
        onClick={() => onChange(!value)}
        className={`relative h-6 w-11 rounded-full transition ${value ? "bg-brand" : "bg-[#d8d7d2]"}`}
      >
        <span
          className={`absolute top-1 size-4 rounded-full bg-white transition ${
            value ? "left-6" : "left-1"
          }`}
        />
      </button>
    </div>
  );
}

function NumberRow({
  label,
  suffix,
  value,
  min,
  onChange,
}: {
  label: string;
  suffix: string;
  value: number;
  min: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-6 py-4">
      <p className="text-sm font-medium text-ink">{label}</p>
      <label className="flex items-center gap-2">
        <input
          type="number"
          min={min}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          className="h-8 w-24 rounded-[10px] border border-line bg-[#efefeb] px-3 text-right text-xs text-ink outline-none"
        />
        <span className="w-16 text-xs text-muted">{suffix}</span>
      </label>
    </div>
  );
}

