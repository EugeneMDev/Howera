"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

import { describePollingActivity } from "@/shared/hooks/use-bounded-polling";
import { ErrorState, LoadingState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";
import { formatDateTime } from "@/shared/lib/format-date";
import { Input } from "@/shared/ui/input";
import { NoLeakNotFoundState } from "@/shared/ui/no-leak-not-found-state";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { JobLifecycleTimeline } from "@/features/jobs/components/job-lifecycle-timeline";
import {
  useJobDetail,
  useJobLifecycleActions,
} from "@/features/jobs/hooks";
import {
  DEFAULT_RETRY_MODEL_PROFILE,
  createClientRequestId,
  getJobLifecycleActionDisabledState,
  getJobLifecycleActionAvailability,
} from "@/features/jobs/lifecycle";
import { JobStatusBadge } from "@/features/jobs/status";

interface JobDetailScreenProps {
  jobId: string;
}

export function JobDetailScreen({ jobId }: JobDetailScreenProps) {
  const { error, job, lastRefreshedAt, notFound, refresh, status } = useJobDetail(jobId);
  const [videoUri, setVideoUri] = useState("");
  const [retryClientRequestId, setRetryClientRequestId] = useState("");
  const [retryModelProfile, setRetryModelProfile] = useState(DEFAULT_RETRY_MODEL_PROFILE);
  const lifecycleActions = useJobLifecycleActions({
    currentStatus: job?.status,
    jobId,
    projectId: job?.project_id,
  });
  const actionAvailability = job ? getJobLifecycleActionAvailability(job) : null;
  const actionDisabledState = actionAvailability
    ? getJobLifecycleActionDisabledState(actionAvailability, lifecycleActions.pendingAction)
    : null;
  const lifecyclePollingSummary = describePollingActivity(lifecycleActions.polling, {
    activePrefix: lifecycleActions.polling.reason ?? undefined,
    idleMessage: "Auto-refresh is idle.",
    stoppedPrefix: lifecycleActions.polling.reason ?? undefined,
  });

  useEffect(() => {
    if (!job?.manifest?.video_uri) {
      return;
    }

    setVideoUri(job.manifest.video_uri);
  }, [job?.manifest?.video_uri]);

  useEffect(() => {
    setRetryClientRequestId((current) => current || createClientRequestId());
  }, []);

  if (status === "loading") {
    return (
      <Panel variant="strong">
        <LoadingState
          description="Loading the latest job status from the API."
          title="Fetching job"
        />
      </Panel>
    );
  }

  if (notFound) {
    return (
      <Panel variant="strong">
        <NoLeakNotFoundState
          resourceName="job"
          returnHref="/jobs"
          returnLabel="Back to jobs"
        />
      </Panel>
    );
  }

  if (!job || status === "error") {
    return (
      <Panel variant="strong">
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
          description={error ?? "Job details could not be loaded."}
          title="Job detail unavailable"
        />
      </Panel>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Panel variant="strong">
        <PanelHeader>
          <p className="eyebrow text-[var(--brand-primary-strong)]">Job detail</p>
          <PanelTitle className="text-4xl">{job.id}</PanelTitle>
          <PanelDescription>
            Contract status is rendered directly from the backend payload and refreshes through{" "}
            <code className="rounded bg-white/70 px-1 py-0.5 text-xs">{"GET /jobs/{jobId}"}</code>.
          </PanelDescription>
        </PanelHeader>

        <div className="flex flex-wrap items-center gap-3">
          <JobStatusBadge status={job.status} />
          <span className="text-sm text-[var(--text-secondary)]">Project {job.project_id}</span>
          <span className="text-sm text-[var(--text-secondary)]">
            Created {formatDateTime(job.created_at)}
          </span>
          {job.updated_at ? (
            <span className="text-sm text-[var(--text-secondary)]">
              Updated {formatDateTime(job.updated_at)}
            </span>
          ) : null}
        </div>

        <div className="mt-5 flex flex-wrap gap-4 text-sm font-medium">
          <Link
            className="text-[var(--brand-primary-strong)] hover:underline"
            href={`/projects/${job.project_id}/jobs`}
          >
            Back to project jobs
          </Link>
          <Link className="text-[var(--brand-primary-strong)] hover:underline" href="/jobs">
            Back to jobs
          </Link>
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <Panel>
          <PanelHeader>
            <p className="eyebrow text-[var(--text-muted)]">Lifecycle timeline</p>
            <PanelTitle>Backend status progression</PanelTitle>
            <PanelDescription>
              The highlighted row is the current backend `JobStatus`. Auto-refresh is bounded and
              only runs after lifecycle actions are submitted.
            </PanelDescription>
          </PanelHeader>

          <JobLifecycleTimeline job={job} />
        </Panel>

        <div className="space-y-4">
          <Panel variant="muted">
            <PanelHeader>
              <p className="eyebrow text-[var(--text-muted)]">Lifecycle controls</p>
              <PanelTitle>Valid next actions</PanelTitle>
              <PanelDescription>
                Actions are gated from the current job status and still rely on the API for final
                FSM enforcement.
              </PanelDescription>
            </PanelHeader>

            <div className="space-y-5">
              {actionAvailability?.canConfirmUpload ? (
                <form
                  className="rounded-[var(--radius-card)] border bg-white/60 p-4"
                  style={{ borderColor: "var(--line-subtle)" }}
                  onSubmit={(event) => {
                    event.preventDefault();
                    void lifecycleActions.confirmUploadByVideoUri(videoUri);
                  }}
                >
                  <p className="eyebrow text-[var(--brand-primary-strong)]">Confirm upload</p>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                    MVP flow is confirm-by-<code className="rounded bg-white px-1 py-0.5 text-xs">video_uri</code>.
                    There is no browser-native source video upload handshake in the current contract.
                  </p>
                  <label className="mt-4 block">
                    <span className="mb-2 block text-sm font-medium text-[var(--text-secondary)]">
                      Video URI
                    </span>
                    <Input
                      disabled={actionDisabledState?.inputDisabled}
                      placeholder="gs://bucket/demo-video.mp4"
                      value={videoUri}
                      onChange={(event) => {
                        setVideoUri(event.target.value);
                      }}
                    />
                  </label>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button disabled={actionDisabledState?.confirmUploadDisabled ?? true} type="submit">
                      {lifecycleActions.isActionPending("confirm-upload")
                        ? "Confirming upload..."
                        : "Confirm upload"}
                    </Button>
                  </div>
                </form>
              ) : (
                <div
                  className="rounded-[var(--radius-card)] border bg-white/55 px-4 py-4"
                  style={{ borderColor: "var(--line-subtle)" }}
                >
                  <p className="eyebrow text-[var(--text-muted)]">Confirm upload</p>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                    Confirm-by-video_uri is available only while the job is still waiting for upload
                    confirmation.
                  </p>
                </div>
              )}

              <div
                className="rounded-[var(--radius-card)] border bg-white/60 p-4"
                style={{ borderColor: "var(--line-subtle)" }}
              >
                <p className="eyebrow text-[var(--text-muted)]">Dispatch actions</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button
                    disabled={actionDisabledState?.runDisabled ?? true}
                    onClick={() => {
                      void lifecycleActions.runWorkflow();
                    }}
                  >
                    {lifecycleActions.isActionPending("run") ? "Starting..." : "Run workflow"}
                  </Button>
                  <Button
                    disabled={actionDisabledState?.cancelDisabled ?? true}
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      void lifecycleActions.cancelCurrentJob();
                    }}
                  >
                    {lifecycleActions.isActionPending("cancel") ? "Cancelling..." : "Cancel job"}
                  </Button>
                </div>
                <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
                  `run` is shown only from{" "}
                  <code className="rounded bg-white px-1 py-0.5 text-xs">UPLOADED</code>. `cancel`
                  stays available on non-terminal states and still relies on API conflict handling if
                  the FSM rejects it.
                </p>
              </div>

              {actionAvailability?.canRetry ? (
                <form
                  className="rounded-[var(--radius-card)] border bg-white/60 p-4"
                  style={{ borderColor: "var(--line-subtle)" }}
                  onSubmit={(event) => {
                    event.preventDefault();
                    void lifecycleActions.retryFailedJob(retryModelProfile, retryClientRequestId);
                  }}
                >
                  <p className="eyebrow text-[var(--brand-primary-strong)]">Retry failed job</p>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                    Retry requires a `model_profile` and unique `client_request_id`. The current UI
                    uses <code className="rounded bg-white px-1 py-0.5 text-xs">cloud-default</code>{" "}
                    as the default profile because backend tests already exercise it.
                  </p>
                  <div className="mt-4 grid gap-4">
                    <label className="block">
                      <span className="mb-2 block text-sm font-medium text-[var(--text-secondary)]">
                        Model profile
                      </span>
                      <Input
                        disabled={actionDisabledState?.inputDisabled}
                        value={retryModelProfile}
                        onChange={(event) => {
                          setRetryModelProfile(event.target.value);
                        }}
                      />
                    </label>

                    <label className="block">
                      <span className="mb-2 block text-sm font-medium text-[var(--text-secondary)]">
                        Client request ID
                      </span>
                      <Input
                        disabled={actionDisabledState?.inputDisabled}
                        value={retryClientRequestId}
                        onChange={(event) => {
                          setRetryClientRequestId(event.target.value);
                        }}
                      />
                    </label>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button disabled={actionDisabledState?.retryDisabled ?? true} type="submit">
                      {lifecycleActions.isActionPending("retry") ? "Retrying..." : "Retry job"}
                    </Button>
                    <Button
                      disabled={actionDisabledState?.inputDisabled}
                      type="button"
                      variant="ghost"
                      onClick={() => {
                        setRetryClientRequestId(createClientRequestId());
                      }}
                    >
                      New request ID
                    </Button>
                  </div>
                </form>
              ) : null}

              <div
                className="rounded-[var(--radius-card)] border bg-white/55 px-4 py-4"
                style={{ borderColor: "var(--line-subtle)" }}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="eyebrow text-[var(--text-muted)]">Freshness</p>
                    <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                      Last successful detail refresh: {formatDateTime(lastRefreshedAt)}
                    </p>
                    {lifecycleActions.polling.reason || lifecycleActions.polling.startedAt ? (
                      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                        {lifecyclePollingSummary}
                      </p>
                    ) : null}
                    {lifecycleActions.polling.lastPolledAt ? (
                      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                        Last auto-refresh tick: {formatDateTime(
                          lifecycleActions.polling.lastPolledAt,
                        )}
                      </p>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => {
                        refresh();
                      }}
                    >
                      Refresh now
                    </Button>
                    {lifecycleActions.polling.active ? (
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => {
                          lifecycleActions.stopPolling();
                        }}
                      >
                        Stop auto-refresh
                      </Button>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
          </Panel>

          {lifecycleActions.feedback ? (
            <Panel variant={lifecycleActions.feedback.tone === "danger" ? "strong" : "muted"}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="eyebrow text-[var(--text-muted)]">Action feedback</p>
                  <h3 className="display-title mt-2 text-xl font-semibold">
                    {lifecycleActions.feedback.title}
                  </h3>
                  <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
                    {lifecycleActions.feedback.description}
                  </p>
                </div>
                <Button
                  size="compact"
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    lifecycleActions.dismissFeedback();
                  }}
                >
                  Dismiss
                </Button>
              </div>
            </Panel>
          ) : null}
        </div>
      </div>

      <Panel>
        <PanelHeader>
          <p className="eyebrow text-[var(--text-muted)]">Artifact manifest</p>
          <PanelTitle>Contract fields</PanelTitle>
          <PanelDescription>The UI surfaces only fields present in the `Job` contract.</PanelDescription>
        </PanelHeader>

        <dl className="grid gap-4 md:grid-cols-2">
          <div
            className="rounded-[var(--radius-card)] border bg-white/55 px-4 py-4"
            style={{ borderColor: "var(--line-subtle)" }}
          >
            <dt className="eyebrow text-[var(--text-muted)]">video_uri</dt>
            <dd className="mt-2 break-all text-sm text-[var(--text-secondary)]">
              {job.manifest?.video_uri ?? "Unavailable"}
            </dd>
          </div>
          <div
            className="rounded-[var(--radius-card)] border bg-white/55 px-4 py-4"
            style={{ borderColor: "var(--line-subtle)" }}
          >
            <dt className="eyebrow text-[var(--text-muted)]">audio_uri</dt>
            <dd className="mt-2 break-all text-sm text-[var(--text-secondary)]">
              {job.manifest?.audio_uri ?? "Unavailable"}
            </dd>
          </div>
          <div
            className="rounded-[var(--radius-card)] border bg-white/55 px-4 py-4"
            style={{ borderColor: "var(--line-subtle)" }}
          >
            <dt className="eyebrow text-[var(--text-muted)]">transcript_uri</dt>
            <dd className="mt-2 break-all text-sm text-[var(--text-secondary)]">
              {job.manifest?.transcript_uri ?? "Unavailable"}
            </dd>
          </div>
          <div
            className="rounded-[var(--radius-card)] border bg-white/55 px-4 py-4"
            style={{ borderColor: "var(--line-subtle)" }}
          >
            <dt className="eyebrow text-[var(--text-muted)]">draft_uri</dt>
            <dd className="mt-2 break-all text-sm text-[var(--text-secondary)]">
              {job.manifest?.draft_uri ?? "Unavailable"}
            </dd>
          </div>
        </dl>
      </Panel>
    </div>
  );
}
