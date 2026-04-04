import React from "react";

import type { Job } from "@/features/jobs/api";
import {
  PRIMARY_LIFECYCLE_STATUSES,
  TERMINAL_LIFECYCLE_STATUSES,
  getLifecycleTimelineState,
} from "@/features/jobs/lifecycle";
import { cn } from "@/shared/lib/cn";
import { formatDateTime } from "@/shared/lib/format-date";
import { JobStatusBadge } from "@/features/jobs/status";

interface JobLifecycleTimelineProps {
  job: Job;
}

export function JobLifecycleTimeline({ job }: JobLifecycleTimelineProps) {
  return (
    <div className="space-y-4">
      {TERMINAL_LIFECYCLE_STATUSES.includes(job.status) ? (
        <div
          className="rounded-[var(--radius-card)] border px-4 py-4"
          style={{ borderColor: "var(--status-danger-soft)", background: "rgba(191, 90, 67, 0.08)" }}
        >
          <div className="flex flex-wrap items-center gap-3">
            <JobStatusBadge status={job.status} />
            <p className="text-sm text-[var(--text-secondary)]">
              Terminal status recorded {formatDateTime(job.updated_at ?? job.created_at)}
            </p>
          </div>
          <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
            The canonical happy-path sequence is shown below for orientation, but this job is
            currently in a terminal state.
          </p>
        </div>
      ) : null}

      <ol className="space-y-3">
        {PRIMARY_LIFECYCLE_STATUSES.map((status) => {
          const timelineState = getLifecycleTimelineState(status, job.status);
          const isCompleted = timelineState === "completed";
          const isCurrent = timelineState === "current";

          return (
            <li
              key={status}
              className={cn(
                "rounded-[var(--radius-card)] border px-4 py-4 transition-colors",
                isCurrent
                  ? "bg-[var(--brand-soft)]"
                  : isCompleted
                    ? "bg-white/65"
                    : "bg-white/35",
              )}
              style={{ borderColor: isCurrent ? "var(--brand-primary)" : "var(--line-subtle)" }}
            >
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="eyebrow text-[var(--text-muted)]">FSM status</p>
                  <div className="mt-2 flex flex-wrap items-center gap-3">
                    <h3 className="display-title text-xl font-semibold">{status}</h3>
                    {isCurrent ? <JobStatusBadge status={status} /> : null}
                  </div>
                </div>

                <p className="text-sm text-[var(--text-secondary)]">
                  {status === "CREATED"
                    ? `Created ${formatDateTime(job.created_at)}`
                    : isCurrent
                      ? `Current status updated ${formatDateTime(job.updated_at ?? job.created_at)}`
                      : isCompleted
                        ? "Reached on the current happy-path progression."
                        : "Pending or not yet observed."}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
