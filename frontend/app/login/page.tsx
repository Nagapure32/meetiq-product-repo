import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen bg-shell lg:grid-cols-[minmax(0,1fr)_480px]">
      <section className="order-2 flex min-h-[420px] flex-col justify-between bg-brand p-6 text-white sm:p-8 lg:order-1 lg:min-h-screen lg:p-10">
        <div>
          <div className="flex items-center gap-3">
            <img
              src="/aress_software_logo.png"
              alt="Aress MeetIQ logo"
              className="size-20 rounded-[12px] bg-white object-contain p-2"
            />
            <div>
              <p className="text-xl font-semibold">Aress MeetIQ</p>
              <p className="mt-1 font-mono text-[11px] uppercase text-white/50">Meeting intelligence</p>
            </div>
          </div>
        </div>

        <div className="my-12 max-w-[680px] lg:my-0">
          <h1 className="max-w-[620px] text-4xl font-semibold leading-tight sm:text-5xl">
            Turn every meeting into decisions, tasks, and searchable knowledge.
          </h1>
          <p className="mt-5 max-w-[540px] text-sm leading-6 text-white/70">
            Connect Microsoft 365, approve bot joins, and let Aress MeetIQ organize meeting notes,
            transcripts, summaries, and follow-ups.
          </p>

          <div className="mt-8 grid max-w-[640px] gap-3 rounded-[14px] border border-white/15 bg-white/10 p-4 shadow-[0_18px_60px_rgba(0,0,0,0.18)] backdrop-blur sm:grid-cols-[1fr_180px]">
            <div className="rounded-[12px] bg-white p-4 text-ink shadow-panel">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[13px] font-semibold">Product sync summary</p>
                  <p className="mt-1 text-[11px] text-muted">Today, 10:30 AM - Microsoft Teams</p>
                </div>
                <span className="rounded-full bg-brand-soft px-2 py-1 text-[10px] font-medium text-brand-dark">
                  Ready
                </span>
              </div>
              <div className="mt-4 space-y-2">
                <PreviewRow label="Decision" text="Launch scope approved for beta workspace." />
                <PreviewRow label="Action" text="Assign owners for transcript review and QA." />
                <PreviewRow label="Search" text="Find decisions, risks, and customer mentions." />
              </div>
            </div>

            <div className="grid content-between gap-3 rounded-[12px] border border-white/15 bg-[#211b7d] p-4">
              <Metric value="24" label="Action items captured" />
              <Metric value="8" label="Meetings summarized" />
              <Metric value="3" label="Approvals pending" />
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            {["Microsoft 365", "Teams meetings", "Secure workspace"].map((item) => (
              <span
                key={item}
                className="rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-[11px] font-medium text-white/75"
              >
                {item}
              </span>
            ))}
          </div>
        </div>

        <p className="font-mono text-[11px] text-white/40">Aress MeetIQ v2.0</p>
      </section>
      <section className="order-1 flex min-h-screen items-center justify-center p-6 sm:p-8 lg:order-2">
        <div className="w-full max-w-[420px]">
          <p className="font-mono text-[11px] uppercase text-muted">Workspace access</p>
          <h2 className="mt-3 text-2xl font-semibold text-ink">Welcome back</h2>
          <p className="mt-2 text-sm leading-5 text-muted">Sign in to review meetings, approvals, and action items.</p>
          <AuthForm />
        </div>
      </section>
    </main>
  );
}

function PreviewRow({ label, text }: { label: string; text: string }) {
  return (
    <div className="rounded-[10px] border border-line bg-[#faf9f5] p-3">
      <p className="font-mono text-[10px] uppercase text-brand-dark">{label}</p>
      <p className="mt-1 text-[12px] leading-5 text-ink">{text}</p>
    </div>
  );
}

function Metric({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <p className="text-2xl font-semibold leading-none text-white">{value}</p>
      <p className="mt-1 text-[11px] leading-4 text-white/55">{label}</p>
    </div>
  );
}
