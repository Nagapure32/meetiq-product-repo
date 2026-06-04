import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-shell px-4 py-5 sm:px-6 lg:grid lg:grid-cols-[minmax(420px,520px)_minmax(0,1fr)] lg:gap-5 lg:p-5">
      <section className="flex min-h-[calc(100vh-2.5rem)] items-center justify-center rounded-[10px] border border-line bg-white px-4 py-8 shadow-panel sm:px-8 lg:min-h-0 lg:px-10">
        <div className="w-full max-w-[420px]">
          <div className="flex items-center gap-3">
            <img
              src="/aress_software_logo.png"
              alt="Aress MeetIQ logo"
              className="size-14 rounded-[10px] border border-line bg-white object-contain p-1.5"
            />
            <div>
              <p className="text-lg font-semibold leading-6 text-ink">Aress MeetIQ</p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-normal text-muted">Workspace access</p>
            </div>
          </div>

          <div className="mt-8">
            <h1 className="text-2xl font-semibold leading-8 text-ink">Welcome back</h1>
            <p className="mt-2 text-sm leading-5 text-muted">
              Sign in to review today&apos;s meetings, captured decisions, and team follow-ups.
            </p>
          </div>

          <div className="mt-5 grid grid-cols-3 gap-2">
            <ReassuranceCue label="SSO ready" />
            <ReassuranceCue label="Encrypted transcripts" />
            <ReassuranceCue label="Admin-controlled sharing" />
          </div>

          <AuthForm />

          <p className="mt-5 font-mono text-[10px] uppercase text-muted">Aress MeetIQ v2.0</p>
        </div>
      </section>

      <section className="mt-5 hidden items-center rounded-[10px] bg-brand p-4 text-white sm:p-6 lg:mt-0 lg:flex lg:p-8">
        <div className="mx-auto w-full max-w-[680px]">
          <div className="max-w-[520px]">
            <p className="font-mono text-[10px] uppercase text-white/75">Meeting intelligence dashboard</p>
            <h2 className="mt-3 text-3xl font-semibold leading-tight sm:text-4xl">
              Decisions, transcripts, and action items in one secure workspace.
            </h2>
            <p className="mt-4 text-sm leading-6 text-white/70">
              Connect Microsoft 365, summarize Teams discussions, and keep ownership clear after every meeting.
            </p>
          </div>

          <div className="mt-7 rounded-[10px] border border-white/15 bg-white p-3 text-ink shadow-[0_18px_60px_rgba(0,0,0,0.18)] sm:p-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
              <div>
                <p className="text-sm font-semibold">Today&apos;s meetings</p>
                <p className="mt-1 text-[11px] text-muted">4 meetings synced from Microsoft Teams</p>
              </div>
              <span className="rounded-[8px] bg-brand-soft px-2.5 py-1 text-[11px] font-medium text-brand-dark">
                SSO ready
              </span>
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_190px]">
              <div className="space-y-2">
                <MeetingCard time="09:30" title="Product sync" status="Decision captured" />
                <MeetingCard time="11:00" title="Customer review" status="3 action items" />
                <MeetingCard time="14:30" title="Implementation standup" status="Encrypted transcripts" />
              </div>

              <div className="grid gap-2">
                <SignalCard title="Decision captured" detail="Beta rollout approved for workspace admins." />
                <SignalCard title="Admin-controlled sharing" detail="Transcript access limited to assigned teams." />
              </div>
            </div>

            <div className="mt-3 grid gap-2 border-t border-line pt-3 sm:grid-cols-3">
              <Metric value="18" label="action items" />
              <Metric value="7" label="summaries ready" />
              <Metric value="2" label="approvals pending" />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {["Encrypted transcripts", "Admin-controlled sharing", "SSO ready"].map((item) => (
              <span
                key={item}
                className="rounded-[8px] border border-white/15 bg-white/10 px-3 py-1.5 text-[11px] font-medium text-white/75"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function ReassuranceCue({ label }: { label: string }) {
  return (
    <div className="rounded-[8px] border border-line bg-[#faf9f5] px-2.5 py-2 text-center text-[10px] font-medium leading-4 text-muted">
      {label}
    </div>
  );
}

function MeetingCard({ time, title, status }: { time: string; title: string; status: string }) {
  return (
    <div className="grid grid-cols-[46px_minmax(0,1fr)] gap-3 rounded-[8px] border border-line bg-[#faf9f5] p-3">
      <p className="font-mono text-[11px] text-muted">{time}</p>
      <div>
        <p className="truncate text-[13px] font-semibold text-ink">{title}</p>
        <p className="mt-1 text-[11px] leading-4 text-brand-dark">{status}</p>
      </div>
    </div>
  );
}

function SignalCard({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-[8px] border border-line bg-white p-3 shadow-panel">
      <p className="text-[12px] font-semibold text-ink">{title}</p>
      <p className="mt-1 text-[11px] leading-4 text-muted">{detail}</p>
    </div>
  );
}

function Metric({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-[8px] border border-line bg-[#faf9f5] p-3">
      <p className="text-xl font-semibold leading-none text-ink">{value}</p>
      <p className="mt-1 text-[11px] leading-4 text-muted">{label}</p>
    </div>
  );
}
