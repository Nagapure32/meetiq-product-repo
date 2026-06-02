import type { ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold tracking-[-0.3px] text-ink">{title}</h1>
        <p className="mt-1 text-[13px] text-muted">{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

export function Panel({
  title,
  action,
  children,
  className = "",
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-[14px] border border-line bg-white p-5 shadow-panel ${className}`}>
      {title ? (
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-ink">{title}</h2>
          {action}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function StatusPill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "good" | "warn" | "brand" }) {
  const styles = {
    neutral: "border-line bg-[#efefeb] text-muted",
    good: "border-[#c7ead9] bg-[#e6f4ec] text-[#2a7a4b]",
    warn: "border-[#f0dfb5] bg-[#fff5d8] text-[#8a5d00]",
    brand: "border-brand bg-brand-soft text-brand-dark",
  };

  return (
    <span className={`inline-flex min-h-6 items-center justify-center rounded-full border px-2 py-1 text-center font-mono text-[10px] leading-none ${styles[tone]}`}>
      {children}
    </span>
  );
}

export function EmptyBlock({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-[12px] border border-dashed border-line bg-[#faf9f5] p-5 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mx-auto mt-1 max-w-[420px] text-xs leading-5 text-muted">{text}</p>
    </div>
  );
}
