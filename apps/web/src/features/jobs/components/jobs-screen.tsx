"use client";

import React from "react";
import Link from "next/link";

import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { JobCard } from "@/features/jobs/components/job-card";
import { useRecentJobs } from "@/features/jobs/hooks";

export function JobsScreen() {
  const { error, jobs, refresh, status } = useRecentJobs();

  return (
    <div className="flex flex-col gap-4">
      <Panel variant="strong">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="eyebrow text-[var(--brand-primary-strong)]">Known jobs</p>
            <h2 className="display-title mt-3 text-4xl font-semibold">
              Browse jobs already opened in this workspace session.
            </h2>
            <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)] md:text-base">
              The current contract exposes{" "}
              <code className="rounded bg-white/70 px-1 py-0.5 text-xs">{"GET /jobs/{jobId}"}</code>{" "}
              but no global jobs list. This view stays contract-safe by refreshing only job IDs
              created or opened in the current browser session.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button
              disabled={status === "loading"}
              variant="secondary"
              onClick={() => {
                refresh();
              }}
            >
              Refresh jobs
            </Button>
            <Link className="text-sm font-medium text-[var(--brand-primary-strong)] hover:underline" href="/projects">
              Create from projects
            </Link>
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHeader>
          <p className="eyebrow text-[var(--text-muted)]">Session browse surface</p>
          <PanelTitle>Recent owned jobs</PanelTitle>
          <PanelDescription>
            Each row resolves through{" "}
            <code className="rounded bg-white/70 px-1 py-0.5 text-xs">{"GET /jobs/{jobId}"}</code>{" "}
            and drops stale or unauthorized IDs using the backend&apos;s no-leak `404` behavior.
          </PanelDescription>
        </PanelHeader>

        {status === "loading" ? (
          <LoadingState
            description="Loading known jobs from the API."
            title="Fetching jobs"
          />
        ) : status === "error" ? (
          <ErrorState
            action={
              <Button
                size="compact"
                variant="secondary"
                onClick={() => {
                  refresh();
                }}
              >
                Retry
              </Button>
            }
            description={error ?? "Jobs could not be loaded."}
            title="Jobs surface unavailable"
          />
        ) : jobs.length === 0 ? (
          <EmptyState
            actionHint="Create a job from any owned project"
            actionLabel="No recent jobs"
            description="No known job IDs have been created or opened in this browser session yet."
            title="Nothing to browse yet"
          />
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
