"use client";

import { Check, RefreshCw, X } from "lucide-react";
import { useEffect, useMemo, useState, useTransition } from "react";

import { EmptyBlock, Panel, StatusPill } from "@/components/ui";
import { ApprovalItem, decideApproval, listApprovals } from "@/lib/api";
import { getCurrentMeetingStatus } from "@/lib/dashboard-ui";

type Decision = "approve" | "reject";

export function ApprovalsBoard({
  initialApprovals,
  initialMessage = null,
}: {
  initialApprovals: ApprovalItem[];
  initialMessage?: string | null;
}) {
  const [approvals, setApprovals] = useState(initialApprovals);
  const [message, setMessage] = useState<string | null>(initialMessage);
  const [activeApprovalId, setActiveApprovalId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (initialMessage) {
      refresh();
    }
  }, []);

  const counts = useMemo(() => {
    return approvals.reduce(
      (acc, approval) => {
        const status = approval.status.toLowerCase();
        if (status === "approved") {
          acc.approved += 1;
        } else if (status === "pending") {
          acc.pending += 1;
        } else {
          acc.rejected += 1;
        }
        return acc;
      },
      { pending: 0, approved: 0, rejected: 0 },
    );
  }, [approvals]);

  function refresh() {
    setMessage(null);
    startTransition(async () => {
      try {
        setApprovals(await listApprovals());
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Could not refresh approvals.");
      }
    });
  }

  function submitDecision(approvalId: string, decision: Decision) {
    setMessage(null);
    setActiveApprovalId(approvalId);
    startTransition(async () => {
      try {
        const updated = await decideApproval(approvalId, decision);
        setApprovals((current) =>
          current.map((approval) => (approval.id === updated.id ? updated : approval)),
        );
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Approval decision failed.");
      } finally {
        setActiveApprovalId(null);
      }
    });
  }

  const sortedApprovals = [...approvals].sort((left, right) => {
    const leftPending = left.status === "pending" ? 0 : 1;
    const rightPending = right.status === "pending" ? 0 : 1;
    if (leftPending !== rightPending) {
      return leftPending - rightPending;
    }
    return String(right.requested_at ?? "").localeCompare(String(left.requested_at ?? ""));
  });

  return (
    <>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <MetricPanel label="Pending" value={counts.pending} helper="Waiting for a decision" />
        <MetricPanel label="Approved" value={counts.approved} helper="Accepted requests" />
        <MetricPanel label="Rejected / expired" value={counts.rejected} helper="Closed requests" />
      </div>

      <Panel
        title="Approval queue"
        className="mt-5"
        action={
          <button
            type="button"
            onClick={refresh}
            title="Refresh approvals"
            className="inline-flex size-8 items-center justify-center rounded-md border border-line text-muted transition hover:border-brand hover:text-brand"
            disabled={isPending}
          >
            <RefreshCw className={`size-4 ${isPending ? "animate-spin" : ""}`} aria-hidden="true" />
          </button>
        }
      >
        {message ? (
          <div className="mb-4 rounded-lg border border-[#f0dfb5] bg-[#fff5d8] px-3 py-2 text-xs text-[#8a5d00]">
            {message}
          </div>
        ) : null}

        {sortedApprovals.length === 0 ? (
          <EmptyBlock
            title="No approval requests"
            text="When the bot requests approval for a Teams meeting, it will appear here."
          />
        ) : (
          <div className="space-y-3">
            {sortedApprovals.map((approval) => {
              const isActive = activeApprovalId === approval.id;
              const isDecidable = approval.status === "pending";
              const currentStatus = getCurrentMeetingStatus({
                ...approval.meeting,
                approval_status: approval.meeting?.approval_status ?? approval.status,
                status: approval.meeting ? undefined : approval.status,
              });

              return (
                <article
                  key={approval.id}
                  className="rounded-lg border border-line bg-[#faf9f5] p-4"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusPill tone={currentStatus.tone}>{currentStatus.label}</StatusPill>
                        {approval.requested_via ? (
                          <span className="font-mono text-[10px] uppercase text-muted">
                            {approval.requested_via}
                          </span>
                        ) : null}
                      </div>
                      <h3 className="mt-3 text-sm font-semibold text-ink">
                        {approval.meeting?.subject ?? "Untitled meeting"}
                      </h3>
                      <p className="mt-1 text-xs text-muted">
                        {formatRange(approval.meeting?.start_time, approval.meeting?.end_time)}
                      </p>
                      <dl className="mt-4 grid gap-3 text-xs text-muted sm:grid-cols-2 lg:grid-cols-3">
                        <Detail label="Requested" value={formatDateTime(approval.requested_at)} />
                        <Detail label="Expires" value={formatDateTime(approval.expires_at)} />
                        <Detail
                          label="Decided"
                          value={
                            approval.decided_at
                              ? `${formatDateTime(approval.decided_at)} via ${
                                  approval.decided_via ?? "unknown"
                                }`
                              : "Not decided"
                          }
                        />
                      </dl>
                    </div>

                    {isDecidable ? (
                      <div className="flex shrink-0 gap-2">
                        <button
                          type="button"
                          title="Approve"
                          onClick={() => submitDecision(approval.id, "approve")}
                          disabled={isPending || isActive}
                          className="inline-flex items-center gap-2 rounded-md border border-[#c7ead9] bg-[#e6f4ec] px-3 py-2 text-xs font-medium text-[#2a7a4b] transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <Check className="size-4" aria-hidden="true" />
                          Approve
                        </button>
                        <button
                          type="button"
                          title="Reject"
                          onClick={() => submitDecision(approval.id, "reject")}
                          disabled={isPending || isActive}
                          className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-muted transition hover:border-[#f0dfb5] hover:text-[#8a5d00] disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <X className="size-4" aria-hidden="true" />
                          Reject
                        </button>
                      </div>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </Panel>
    </>
  );
}

function MetricPanel({ label, value, helper }: { label: string; value: number; helper: string }) {
  return (
    <Panel title={label}>
      <p className="text-[28px] font-semibold text-ink">{value}</p>
      <p className="mt-2 font-mono text-[11px] text-muted">{helper}</p>
    </Panel>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-mono text-[10px] uppercase text-muted">{label}</dt>
      <dd className="mt-1 break-words text-ink">{value}</dd>
    </div>
  );
}

function formatRange(start?: string | null, end?: string | null) {
  if (!start || !end) {
    return "Time not available";
  }
  return `${formatDateTime(start)} - ${formatTime(end)}`;
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Not set";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    timeStyle: "short",
  }).format(new Date(value));
}
