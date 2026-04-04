import React from "react";

import Link from "next/link";

import type { Job } from "@/features/jobs/api";
import { JobStatusBadge } from "@/features/jobs/status";
import { formatDateTime } from "@/shared/lib/format-date";

interface JobCardProps {
  job: Job;
}

export function JobCard({ job }: JobCardProps) {
  return (
    <article
      className="rounded-[var(--radius-card)] border bg-white/55 px-4 py-4"
      style={{ borderColor: "var(--line-subtle)" }}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="eyebrow text-[var(--text-muted)]">{job.id}</p>
          <h3 className="display-title mt-2 text-2xl font-semibold">Project {job.project_id}</h3>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <JobStatusBadge status={job.status} />
            <span className="text-sm text-[var(--text-secondary)]">
              Created {formatDateTime(job.created_at)}
            </span>
            {job.updated_at ? (
              <span className="text-sm text-[var(--text-secondary)]">
                Updated {formatDateTime(job.updated_at)}
              </span>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap gap-4 text-sm font-medium">
          <Link className="text-[var(--brand-primary-strong)] hover:underline" href={`/jobs/${job.id}`}>
            Open job
          </Link>
          <Link
            className="text-[var(--brand-primary-strong)] hover:underline"
            href={`/projects/${job.project_id}/jobs`}
          >
            Project jobs
          </Link>
        </div>
      </div>
    </article>
  );
}
