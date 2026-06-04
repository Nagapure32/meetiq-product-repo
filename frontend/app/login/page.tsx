import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen grid-cols-[1fr_480px] bg-shell">
      <section className="flex flex-col justify-between bg-brand p-10 text-white">
        <div className="flex items-center gap-3">
          <img
            src="/aress_software_logo.png"
            alt="Aress MeetIQ logo"
            className="size-20 rounded-[12px] bg-white object-contain p-2"
          />
          <span className="text-xl font-semibold">Aress MeetIQ</span>
        </div>
        <div className="max-w-[620px]">
          <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-white/50">Meeting intelligence</p>
          <h1 className="mt-4 text-5xl font-semibold leading-tight tracking-[-1px]">
            Turn Teams meetings into searchable decisions, tasks, and follow-ups.
          </h1>
          <p className="mt-5 max-w-[520px] text-sm leading-6 text-white/70">
            Connect your Microsoft calendar, approve bot joins, and let Aress MeetIQ organize transcripts,
            summaries, and action items.
          </p>
        </div>
        <p className="font-mono text-[11px] text-white/40">Aress MeetIQ v2.0</p>
      </section>
      <section className="flex items-center justify-center p-8">
        <div>
          <h2 className="text-2xl font-semibold tracking-[-0.4px] text-ink">Welcome</h2>
          <p className="mt-2 text-sm text-muted">Log in or create your workspace account.</p>
          <div className="mt-6">
            <AuthForm />
          </div>
        </div>
      </section>
    </main>
  );
}
