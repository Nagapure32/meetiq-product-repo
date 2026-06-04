"use client";

import { CalendarDays } from "lucide-react";
import Link from "next/link";
import { useEffect, useState, useTransition } from "react";
import {
  bootstrapUserWorkspace,
  getMeetingAssistantSettings,
  updateMeetingAssistantSettings,
} from "@/lib/api";
import { microsoftOAuthOptions } from "@/lib/microsoft-oauth";
import { supabaseBrowserClient } from "@/lib/supabase/client";
import { StatusPill } from "@/components/ui";

type ConnectionStatus = "idle" | "connected" | "enabled" | "error";

export default function OnboardingPage() {
  const [status, setStatus] = useState<ConnectionStatus>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    startTransition(async () => {
      const {
        data: { session },
      } = await supabaseBrowserClient.auth.getSession();
      if (!session?.user) {
        return;
      }

      try {
        await bootstrapUserWorkspace(extractMicrosoftIdentity(session.user));
        setStatus("connected");
      } catch {
        setStatus("error");
        setMessage("Could not prepare your Microsoft calendar connection.");
      }
    });
  }, []);

  function connectWithMicrosoft() {
    setMessage(null);
    startTransition(async () => {
      const { error } = await supabaseBrowserClient.auth.signInWithOAuth({
        provider: "azure",
        options: microsoftOAuthOptions(`${window.location.origin}/onboarding`),
      });
      if (error) {
        setStatus("error");
        setMessage(error.message);
      }
    });
  }

  function enableCalendarAssistant() {
    setMessage(null);
    startTransition(async () => {
      try {
        const {
          data: { session },
        } = await supabaseBrowserClient.auth.getSession();
        if (!session?.user) {
          await connectWithMicrosoft();
          return;
        }

        await bootstrapUserWorkspace(extractMicrosoftIdentity(session.user));
        const currentSettings = await getMeetingAssistantSettings();
        await updateMeetingAssistantSettings({
          ...currentSettings,
          auto_join_enabled: true,
        });
        setStatus("enabled");
        setMessage("Calendar assistant enabled for your Microsoft calendar.");
      } catch {
        setStatus("error");
        setMessage("Could not enable the calendar assistant. Check that FastAPI is running.");
      }
    });
  }

  return (
    <main className="min-h-screen bg-shell">
      <div className="grid min-h-screen grid-cols-[280px_1fr] overflow-hidden bg-shell">
        <aside className="bg-brand p-8 text-white">
          <div className="flex items-center gap-3">
            <img
              src="/aress_software_logo.png"
              alt="Aress MeetIQ logo"
              className="size-16 rounded-[12px] bg-white object-contain p-2"
            />
            <p className="text-lg font-semibold">Aress MeetIQ</p>
          </div>
          <div className="mt-14 space-y-8 text-sm">
            <Step number="1" label="Create account" done />
            <Step number="2" label="Connect calendar" active={status !== "enabled"} done={status === "enabled"} />
            <Step number="3" label="Review dashboard" active={status === "enabled"} />
            <Step number="4" label="Join or create team" />
          </div>
          <p className="mt-64 font-mono text-[11px] text-white/40">Aress MeetIQ v2.0</p>
        </aside>
        <section className="p-12">
          <h1 className="text-[22px] font-semibold tracking-[-0.4px] text-ink">
            Connect your calendar
          </h1>
          <p className="mt-3 max-w-[520px] text-[13px] leading-5 text-muted">
            Aress MeetIQ uses your Microsoft calendar to detect upcoming Teams meetings and send the bot to join on your behalf.
          </p>
          <div className="mt-8 rounded-[14px] border border-line bg-white p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="grid size-10 place-items-center rounded-[10px] bg-[#e8f2fd] text-[#1a5fa8]">
                  <CalendarDays size={20} />
                </div>
                <div>
                  <p className="text-[13px] font-semibold text-ink">Microsoft Outlook</p>
                  <p className="mt-1 text-[11px] text-muted">
                    Exchange - Microsoft 365 - Azure AD
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusPill tone={status === "enabled" ? "good" : status === "error" ? "warn" : "neutral"}>
                  {status === "enabled" ? "Enabled" : status === "connected" ? "Connected" : "Not enabled"}
                </StatusPill>
                <button
                  type="button"
                  onClick={status === "idle" ? connectWithMicrosoft : enableCalendarAssistant}
                  disabled={isPending || status === "enabled"}
                  className="h-[30px] rounded-[10px] border border-brand px-4 text-[11px] font-medium text-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isPending
                    ? "Working..."
                    : status === "enabled"
                      ? "Assistant enabled"
                      : status === "idle"
                      ? "Connect with Microsoft"
                      : "Enable assistant"}
                </button>
                {status === "enabled" ? (
                  <Link
                    href="/"
                    className="grid h-[30px] place-items-center rounded-[10px] bg-brand px-4 text-[11px] font-medium text-white"
                  >
                    Go to dashboard
                  </Link>
                ) : null}
              </div>
            </div>
            {message ? <p className="mt-4 text-xs leading-5 text-muted">{message}</p> : null}
          </div>
          <div className="mt-6 rounded-[14px] border border-line bg-white p-5 opacity-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[13px] font-semibold text-ink">Google Calendar</p>
                <p className="mt-1 text-[11px] text-muted">Post-MVP</p>
              </div>
              <StatusPill>Coming soon</StatusPill>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Step({
  number,
  label,
  active = false,
  done = false,
}: {
  number: string;
  label: string;
  active?: boolean;
  done?: boolean;
}) {
  return (
    <div className="flex items-center gap-4">
      <span className={`grid size-7 place-items-center rounded-full text-xs font-semibold ${active || done ? "bg-white text-brand" : "bg-white/15 text-white/50"}`}>
        {done ? "OK" : number}
      </span>
      <span className={active ? "font-medium text-white" : "text-white/50"}>{label}</span>
    </div>
  );
}

function extractMicrosoftIdentity(user: {
  email?: string;
  id: string;
  identities?: Array<{
    provider?: string;
    provider_id?: string;
    identity_data?: Record<string, unknown>;
  }>;
}) {
  const azureIdentity = user.identities?.find((identity) => identity.provider === "azure");
  const identityData = azureIdentity?.identity_data ?? {};
  const email = asString(identityData.email) ?? asString(identityData.preferred_username) ?? user.email;

  return {
    email,
    tenant_id: asString(identityData.tid) ?? asString(identityData.tenant_id),
    aad_user_id:
      azureIdentity?.provider_id ??
      asString(identityData.oid) ??
      asString(identityData.sub) ??
      user.id,
  };
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}
