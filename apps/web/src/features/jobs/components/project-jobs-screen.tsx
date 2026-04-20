"use client";

import React, { useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";
import { NoLeakNotFoundState } from "@/shared/ui/no-leak-not-found-state";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { JobCard } from "@/features/jobs/components/job-card";
import { useCreateJob, useRecentJobs } from "@/features/jobs/hooks";
import { useProjectDetail } from "@/features/projects/hooks";

interface ProjectJobsScreenProps {
  projectId: string;
}

export function ProjectJobsScreen({ projectId }: ProjectJobsScreenProps) {
  const projectQuery = useProjectDetail(projectId);
  const jobsQuery = useRecentJobs(projectId);
  const createJob = useCreateJob(projectId);
  const [createdJobId, setCreatedJobId] = useState<string | null>(null);

  if (projectQuery.status === "loading") {
    return (
      <Panel variant="strong">
        <LoadingState
          description="Resolving the project before jobs load."
          title="Fetching project context"
        />
      </Panel>
    );
  }

  if (projectQuery.notFound) {
    return (
      <Panel variant="strong">
        <NoLeakNotFoundState resourceName="project" />
      </Panel>
    );
  }

  if (!projectQuery.project || projectQuery.status === "error") {
    return (
      <Panel variant="strong">
        <ErrorState
          action={
            <Button
              size="compact"
              variant="secondary"
              onClick={() => {
                projectQuery.refresh();
              }}
            >
              Retry
            </Button>
          }
          description={projectQuery.error ?? "Project context could not be loaded."}
          title="Project jobs unavailable"
        />
      </Panel>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Panel variant="strong">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
          <div className="max-w-3xl">
            <p className="eyebrow text-[var(--brand-primary-strong)]">Project jobs</p>
            <h2 className="display-title mt-3 text-4xl font-semibold">{projectQuery.project.name}</h2>
            <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)] md:text-base">
              Job creation uses{" "}
              <code className="rounded bg-white/70 px-1 py-0.5 text-xs">
                {"POST /projects/{projectId}/jobs"}
              </code>
              . The list below refreshes in place using known job IDs for this project and
              contract-safe{" "}
              <code className="rounded bg-white/70 px-1 py-0.5 text-xs">{"GET /jobs/{jobId}"}</code>{" "}
              reads.
            </p>
          </div>

          <form
            className="rounded-[var(--radius-card)] border bg-white/55 p-4"
            style={{ borderColor: "var(--line-subtle)" }}
            onSubmit={(event) => {
              event.preventDefault();
              void createJob.submit().then((job) => {
                if (!job) {
                  return;
                }

                setCreatedJobId(job.id);
              });
            }}
          >
            <PanelHeader className="mb-4 gap-1">
              <p className="eyebrow text-[var(--text-muted)]">Create job</p>
              <PanelTitle className="text-2xl">New job under {projectQuery.project.id}</PanelTitle>
              <PanelDescription>
                No additional fields are sent in v1. The backend returns the contract ID and initial
                `CREATED` status.
              </PanelDescription>
            </PanelHeader>

            {createJob.error ? (
              <p className="text-sm text-[var(--status-danger)]">{createJob.error}</p>
            ) : null}

            {createdJobId ? (
              <p className="text-sm text-[var(--status-success)]">Job created: {createdJobId}</p>
            ) : null}

            <div className="mt-4 flex flex-wrap gap-3">
              <Button disabled={createJob.isSubmitting} type="submit">
                {createJob.isSubmitting ? "Creating job..." : "Create job"}
              </Button>
              <Button
                disabled={jobsQuery.status === "loading"}
                type="button"
                variant="secondary"
                onClick={() => {
                  jobsQuery.refresh();
                }}
              >
                Refresh jobs
              </Button>
            </div>
          </form>
        </div>
      </Panel>

      <Panel>
        <PanelHeader>
          <p className="eyebrow text-[var(--text-muted)]">Known jobs for this project</p>
          <PanelTitle>Project-scoped browse surface</PanelTitle>
          <PanelDescription>
            This list contains jobs created or opened in the current browser session for this project.
          </PanelDescription>
        </PanelHeader>

        {jobsQuery.status === "loading" ? (
          <LoadingState
            description="Loading jobs for this project."
            title="Fetching project jobs"
          />
        ) : jobsQuery.status === "error" ? (
          <ErrorState
            action={
              <Button
                size="compact"
                variant="secondary"
                onClick={() => {
                  jobsQuery.refresh();
                }}
              >
                Retry
              </Button>
            }
            description={jobsQuery.error ?? "Jobs could not be loaded for this project."}
            title="Project jobs unavailable"
          />
        ) : jobsQuery.jobs.length === 0 ? (
          <EmptyState
            actionHint="Create the first job for this project"
            actionLabel="Waiting for jobs"
            description="No jobs are known for this project in the current browser session yet."
            title="No project jobs yet"
          />
        ) : (
          <div className="space-y-3">
            {jobsQuery.jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
