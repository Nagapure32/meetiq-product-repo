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
              Sign in to your MeetIQ workspace.
            </p>
          </div>

          <p className="mt-5 rounded-[8px] border border-line bg-[#fbfaf7] px-3 py-2 text-[11px] leading-5 text-muted">
            Microsoft sign-in keeps calendar and Teams access connected.
          </p>

          <AuthForm />

          <p className="mt-5 font-mono text-[10px] uppercase text-muted">Aress MeetIQ v2.0</p>
        </div>
      </section>

      <section className="mt-5 hidden items-center rounded-[10px] border border-line bg-[#eeedfd] p-4 text-ink sm:p-6 lg:mt-0 lg:flex lg:p-8">
        <div className="mx-auto w-full max-w-[620px]">
          <div className="max-w-[520px]">
            <p className="font-mono text-[10px] uppercase text-brand-dark">Meeting intelligence</p>
            <h2 className="mt-4 text-3xl font-semibold leading-tight text-ink sm:text-4xl">
              A quieter way to leave every meeting with clarity.
            </h2>
            <p className="mt-4 max-w-[460px] text-sm leading-6 text-muted">
              MeetIQ turns Teams conversations into concise summaries, decisions, and follow-ups without adding noise to your day.
            </p>
          </div>

          <div className="mt-10 max-w-[480px] rounded-[10px] border border-line bg-white p-5 shadow-panel">
            <p className="font-mono text-[10px] uppercase text-brand-dark">Decision captured</p>
            <p className="mt-3 text-lg font-semibold leading-7 text-ink">
              Move launch review to Friday.
            </p>
            <p className="mt-2 text-xs leading-5 text-muted">
              Owner assigned, follow-up drafted, and transcript linked to the source meeting.
            </p>
          </div>

          <div className="mt-8 grid max-w-[480px] gap-3 sm:grid-cols-3">
            <TrustPoint label="SSO ready" />
            <TrustPoint label="Private notes" />
            <TrustPoint label="Clear owners" />
          </div>
        </div>
      </section>
    </main>
  );
}

function TrustPoint({ label }: { label: string }) {
  return (
    <div className="rounded-[8px] border border-[#d8d6ff] bg-white/55 px-3 py-2 text-center text-[11px] font-medium leading-4 text-brand-dark">
      {label}
    </div>
  );
}
