import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-white lg:grid lg:grid-cols-[minmax(0,1fr)_480px] xl:grid-cols-[minmax(0,1fr)_520px]">
      <section className="relative hidden min-h-screen overflow-hidden bg-[#5b9fd8] text-white lg:flex">
        <div className="absolute inset-0 bg-[linear-gradient(160deg,rgba(105,179,231,0.94),rgba(45,103,166,0.98)_54%,#162a73_100%)]" />
        <CloudBand className="left-[-5%] top-[28%] opacity-45" />
        <CloudBand className="left-[18%] top-[43%] opacity-55" />
        <CloudBand className="left-[-9%] bottom-[-8%] opacity-90" dark />

        <div className="relative z-10 flex min-h-screen w-full flex-col justify-between p-10 xl:p-12">
          <div>
            <div className="flex items-center gap-3">
              <img
                src="/aress_software_logo.png"
                alt="Aress MeetIQ logo"
                className="size-20 rounded-[12px] bg-white object-contain p-2 shadow-[0_20px_60px_rgba(16,42,92,0.28)]"
              />
              <div>
                <p className="text-2xl font-semibold leading-7">Aress MeetIQ</p>
                <p className="mt-1 text-xs font-medium text-white/70">Powered by Aress Software</p>
              </div>
            </div>
          </div>

          <PaperPlaneScene />

          <div className="max-w-[560px] pb-4">
            <p className="font-mono text-[10px] uppercase text-white/65">Meeting intelligence</p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight xl:text-5xl">
              From meeting noise to clear next steps.
            </h1>
            <p className="mt-4 max-w-[500px] text-sm leading-6 text-white/75">
              Capture Teams conversations, decisions, owners, and searchable follow-ups in one secure workspace.
            </p>
            <div className="mt-6 grid max-w-[480px] grid-cols-3 gap-3">
              <TrustPoint label="Teams ready" />
              <TrustPoint label="Secure access" />
              <TrustPoint label="Clear owners" />
            </div>
          </div>
        </div>
      </section>

      <section className="flex min-h-screen flex-col justify-between bg-white px-5 py-8 sm:px-8 lg:px-10">
        <div />
        <div className="mx-auto w-full max-w-[420px]">
          <div className="flex flex-col items-center text-center">
            <img
              src="/aress_software_logo.png"
              alt="Aress MeetIQ logo"
              className="size-24 rounded-[16px] bg-white object-contain p-2 shadow-[0_18px_45px_rgba(26,26,24,0.12)]"
            />
            <p className="mt-5 text-2xl font-semibold leading-7 text-ink">Aress MeetIQ</p>
            <p className="mt-2 text-sm leading-5 text-muted">Welcome to your meeting intelligence workspace</p>
          </div>

          <AuthForm />
        </div>

        <div className="mx-auto mt-8 max-w-[420px] text-center">
          <p className="text-xs leading-5 text-muted">
            Copyright (c) 2026 Aress Software. All Rights Reserved.
          </p>
          <p className="mt-1 font-mono text-[10px] text-muted">version: 2.0</p>
        </div>
      </section>
    </main>
  );
}

function TrustPoint({ label }: { label: string }) {
  return (
    <div className="rounded-[8px] border border-white/20 bg-white/15 px-3 py-2 text-center text-[11px] font-medium leading-4 text-white shadow-[0_10px_24px_rgba(16,42,92,0.16)] backdrop-blur">
      {label}
    </div>
  );
}

function PaperPlaneScene() {
  return (
    <div className="relative mx-auto h-[340px] w-full max-w-[680px]" aria-hidden="true">
      <div className="absolute left-[10%] top-[12%] h-[58px] w-[86px] rotate-[26deg] rounded-[8px_40px_8px_8px] bg-[#122f86] shadow-[0_18px_40px_rgba(8,28,90,0.26)]">
        <span className="absolute bottom-2 right-5 size-0 border-y-[9px] border-l-[18px] border-y-transparent border-l-[#ef1f3e]" />
      </div>
      <div className="absolute right-[17%] top-[38%] h-[54px] w-[84px] rotate-[-24deg] rounded-[8px_40px_8px_8px] bg-white shadow-[0_20px_48px_rgba(8,28,90,0.25)]">
        <span className="absolute bottom-2 right-5 size-0 border-y-[8px] border-l-[16px] border-y-transparent border-l-[#ef1f3e]" />
      </div>
      <div className="absolute left-[25%] top-[18%] h-20 w-40 rounded-full border-2 border-dashed border-[#17327f]/65 border-l-transparent border-b-transparent" />
      <div className="absolute right-[30%] top-[48%] h-20 w-48 rounded-full border-2 border-dashed border-white/80 border-r-transparent border-t-transparent" />

      <div className="absolute left-[8%] top-[58%] w-[520px] rounded-[8px] border border-white/18 bg-white/12 p-4 shadow-[0_24px_64px_rgba(8,28,90,0.22)] backdrop-blur">
        <div className="flex items-center justify-between border-b border-white/15 pb-3">
          <div>
            <p className="text-xs font-semibold text-white">Product review sync</p>
            <p className="mt-1 text-[11px] text-white/65">12 decisions captured</p>
          </div>
          <span className="rounded-full bg-white/18 px-3 py-1 text-[10px] font-medium text-white">Live summary</span>
        </div>
        <div className="mt-4 grid grid-cols-[1.2fr_0.8fr] gap-3">
          <div className="rounded-[8px] bg-white p-3 text-ink">
            <p className="text-[11px] font-semibold">Action items</p>
            <div className="mt-3 space-y-2">
              <PreviewLine width="w-[92%]" />
              <PreviewLine width="w-[76%]" />
              <PreviewLine width="w-[84%]" />
            </div>
          </div>
          <div className="rounded-[8px] bg-[#172f85] p-3 text-white">
            <p className="text-[11px] font-semibold">Owners</p>
            <div className="mt-3 space-y-2">
              <PreviewLine width="w-[70%]" light />
              <PreviewLine width="w-[88%]" light />
              <PreviewLine width="w-[58%]" light />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PreviewLine({ width, light = false }: { width: string; light?: boolean }) {
  return <span className={`block h-2 rounded-full ${width} ${light ? "bg-white/40" : "bg-[#e2e1dc]"}`} />;
}

function CloudBand({ className, dark = false }: { className: string; dark?: boolean }) {
  const color = dark ? "bg-[#142a78]" : "bg-white/20";
  return (
    <div className={`absolute flex h-28 w-[900px] items-end ${className}`} aria-hidden="true">
      {Array.from({ length: 10 }).map((_, index) => (
        <span
          key={index}
          className={`${color} block rounded-t-full`}
          style={{
            width: `${92 + (index % 3) * 22}px`,
            height: `${56 + (index % 4) * 18}px`,
            marginLeft: index === 0 ? 0 : -18,
          }}
        />
      ))}
    </div>
  );
}
