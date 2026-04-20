"use client";

import { startTransition, useCallback, useEffect, useState } from "react";

import { describeCommonApiError } from "@/shared/api/error-feedback";
import { ApiClientError, isNoLeakNotFoundError } from "@/shared/api/errors";
import {
  createPollingPausedFeedback,
  hasPollingAttemptWindowEnded,
  useBoundedPolling,
} from "@/shared/hooks/use-bounded-polling";
import {
  useApiClient,
  useInvalidateQuery,
  useQueryVersion,
  useTelemetry,
} from "@/shared/providers/app-providers";
import {
  cancelJob,
  confirmJobUpload,
  createJob,
  getJob,
  retryJob,
  runJob,
  type Job,
  type JobStatus,
} from "@/features/jobs/api";
import {
  type RecentJobRecord,
  filterRecentJobRecords,
  readRecentJobRecords,
  rememberRecentJobRecord,
  writeRecentJobRecords,
} from "@/features/jobs/recent-jobs-session";

type QueryStatus = "loading" | "success" | "error";
type MutationStatus = "idle" | "submitting" | "error";

interface JobsState {
  error: string | null;
  jobs: Job[];
  status: QueryStatus;
}

interface JobDetailState {
  error: string | null;
  job: Job | null;
  lastRefreshedAt: string | null;
  notFound: boolean;
  status: QueryStatus;
}

export interface LifecycleFeedback {
  description: string;
  tone: "danger" | "info" | "success" | "warning";
  title: string;
}

function toErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

function getBrowserSessionStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.sessionStorage;
}

export const RECENT_JOBS_QUERY_KEY = "jobs:recent";

export function jobDetailQueryKey(jobId: string): string {
  return `jobs:${jobId}`;
}

export function projectJobsQueryKey(projectId: string): string {
  return `projects:${projectId}:jobs`;
}

function rememberJobInSession(job: Job): void {
  const storage = getBrowserSessionStorage();
  const records = readRecentJobRecords(storage);

  writeRecentJobRecords(
    storage,
    rememberRecentJobRecord(records, {
      jobId: job.id,
      projectId: job.project_id,
      touchedAt: job.updated_at ?? job.created_at,
    }),
  );
}

function toRecentJobRecord(job: Job): RecentJobRecord {
  return {
    jobId: job.id,
    projectId: job.project_id,
    touchedAt: job.updated_at ?? job.created_at,
  };
}

function reconcileRecentJobRecords(
  existingRecords: RecentJobRecord[],
  jobs: Job[],
  projectId?: string,
): RecentJobRecord[] {
  if (!projectId) {
    return jobs.map(toRecentJobRecord);
  }

  const nextProjectRecords = jobs.map(toRecentJobRecord);
  const unaffectedRecords = existingRecords.filter((record) => record.projectId !== projectId);

  return [...nextProjectRecords, ...unaffectedRecords].slice(0, 24);
}

export function useCreateJob(projectId: string) {
  const apiClient = useApiClient();
  const invalidateQuery = useInvalidateQuery();
  const telemetry = useTelemetry();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<MutationStatus>("idle");

  return {
    error,
    isSubmitting: status === "submitting",
    async submit(): Promise<Job | null> {
      try {
        setError(null);
        setStatus("submitting");
        const job = await createJob(apiClient, projectId);
        rememberJobInSession(job);
        invalidateQuery(projectJobsQueryKey(projectId));
        invalidateQuery(RECENT_JOBS_QUERY_KEY);
        invalidateQuery(jobDetailQueryKey(job.id));
        telemetry.track({
          attributes: {
            action: "create",
            jobId: job.id,
            projectId,
            result: "succeeded",
            status: job.status,
          },
          name: "job.create.succeeded",
        });
        setStatus("idle");
        return job;
      } catch (submitError) {
        telemetry.track({
          attributes: {
            action: "create",
            projectId,
            result: "failed",
          },
          error: submitError,
          name: "job.create.failed",
        });
        setError(
          describeCommonApiError(submitError, {
            actionLabel: "Job creation",
            fallbackDescription: "Job could not be created.",
            failedTitle: "Job creation failed",
            invalidRequestTitle: "Job creation rejected",
            noLeakDescription:
              "The project is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
            noLeakTitle: "Project unavailable",
            rejectedTitle: "Job creation rejected",
          }).description,
        );
        setStatus("error");
        return null;
      }
    },
  };
}

export function useRecentJobs(projectId?: string) {
  const apiClient = useApiClient();
  const invalidateQuery = useInvalidateQuery();
  const queryVersion = useQueryVersion(projectId ? projectJobsQueryKey(projectId) : RECENT_JOBS_QUERY_KEY);
  const [state, setState] = useState<JobsState>({
    error: null,
    jobs: [],
    status: "loading",
  });

  useEffect(() => {
    let cancelled = false;
    const storage = getBrowserSessionStorage();
    const existingRecords = readRecentJobRecords(storage);
    const records = filterRecentJobRecords(existingRecords, projectId);

    if (records.length === 0) {
      setState({
        error: null,
        jobs: [],
        status: "success",
      });
      return undefined;
    }

    setState((current) => ({
      ...current,
      error: null,
      status: current.jobs.length > 0 ? current.status : "loading",
    }));

    void Promise.all(
      records.map(async (record) => {
        try {
          return await getJob(apiClient, record.jobId);
        } catch (error) {
          if (isNoLeakNotFoundError(error)) {
            return null;
          }

          throw error;
        }
      }),
    )
      .then((jobs) => {
        if (cancelled) {
          return;
        }

        const nextJobs = jobs
          .filter((job): job is Job => job !== null)
          .sort((left, right) =>
            (right.updated_at ?? right.created_at).localeCompare(left.updated_at ?? left.created_at),
          );

        writeRecentJobRecords(
          storage,
          reconcileRecentJobRecords(existingRecords, nextJobs, projectId),
        );

        setState({
          error: null,
          jobs: nextJobs,
          status: "success",
        });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }

        setState({
          error: describeCommonApiError(error, {
            actionLabel: "Jobs load",
            fallbackDescription: "Jobs could not be loaded.",
            failedTitle: "Jobs load failed",
            invalidRequestTitle: "Jobs load rejected",
            noLeakDescription:
              "The job context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
            noLeakTitle: "Jobs unavailable",
            rejectedTitle: "Jobs load rejected",
          }).description,
          jobs: [],
          status: "error",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [apiClient, projectId, queryVersion]);

  return {
    ...state,
    refresh() {
      invalidateQuery(projectId ? projectJobsQueryKey(projectId) : RECENT_JOBS_QUERY_KEY);
    },
  };
}

export function useJobDetail(jobId: string) {
  const apiClient = useApiClient();
  const invalidateQuery = useInvalidateQuery();
  const queryVersion = useQueryVersion(jobDetailQueryKey(jobId));
  const [state, setState] = useState<JobDetailState>({
    error: null,
    job: null,
    lastRefreshedAt: null,
    notFound: false,
    status: "loading",
  });

  useEffect(() => {
    let cancelled = false;

    setState((current) => ({
      ...current,
      error: null,
      notFound: false,
      status: current.job ? current.status : "loading",
    }));

    void getJob(apiClient, jobId)
      .then((job) => {
        if (cancelled) {
          return;
        }

        rememberJobInSession(job);
        setState({
          error: null,
          job,
          lastRefreshedAt: new Date().toISOString(),
          notFound: false,
          status: "success",
        });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }

        if (isNoLeakNotFoundError(error)) {
          setState({
            error: null,
            job: null,
            lastRefreshedAt: null,
            notFound: true,
            status: "error",
          });
          return;
        }

        setState({
          error: describeCommonApiError(error, {
            actionLabel: "Job detail load",
            fallbackDescription: "Job details could not be loaded.",
            failedTitle: "Job detail load failed",
            invalidRequestTitle: "Job detail load rejected",
            noLeakDescription:
              "The job is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
            noLeakTitle: "Job unavailable",
            rejectedTitle: "Job detail load rejected",
          }).description,
          job: null,
          lastRefreshedAt: null,
          notFound: false,
          status: "error",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [apiClient, jobId, queryVersion]);

  return {
    ...state,
    refresh() {
      invalidateQuery(jobDetailQueryKey(jobId));
      invalidateQuery(RECENT_JOBS_QUERY_KEY);
    },
  };
}

function describeLifecycleError(actionLabel: string, error: unknown): LifecycleFeedback {
  if (isNoLeakNotFoundError(error)) {
    return {
      description:
        "The job is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
      title: "Job not found",
      tone: "danger",
    };
  }

  if (!(error instanceof ApiClientError)) {
    return {
      description: toErrorMessage(error, `${actionLabel} could not be completed.`),
      title: `${actionLabel} failed`,
      tone: "danger",
    };
  }

  const details =
    typeof error.details === "object" && error.details !== null
      ? (error.details as Record<string, unknown>)
      : null;

  if (error.code === "VIDEO_URI_CONFLICT") {
    return {
      description: `This job already has a different confirmed video URI. Current: ${String(
        details?.current_video_uri ?? "unknown",
      )}. Submitted: ${String(details?.submitted_video_uri ?? "unknown")}.`,
      title: "Video URI conflict",
      tone: "warning",
    };
  }

  if (error.code === "FSM_TRANSITION_INVALID" || error.code === "FSM_TERMINAL_IMMUTABLE") {
    const allowedStatuses = Array.isArray(details?.allowed_next_statuses)
      ? details?.allowed_next_statuses.join(", ")
      : "none";

    return {
      description: `Current status ${String(details?.current_status ?? "unknown")} cannot move to ${String(
        details?.attempted_status ?? "the requested state",
      )}. Allowed next statuses: ${allowedStatuses}.`,
      title: "Lifecycle action blocked",
      tone: "warning",
    };
  }

  if (error.code === "RETRY_NOT_ALLOWED_STATE" || error.code === "JOB_ALREADY_RUNNING") {
    return {
      description:
        error.message ||
        `Retry is not allowed while the job is in ${String(details?.current_status ?? "its current")} state.`,
      title: "Retry rejected",
      tone: "warning",
    };
  }

  if (error.code === "ORCHESTRATOR_DISPATCH_FAILED") {
    return {
      description: "The API rejected the action because workflow dispatch failed upstream.",
      title: "Workflow dispatch failed",
      tone: "danger",
    };
  }

  return describeCommonApiError(error, {
    actionLabel,
    conflictTitle: `${actionLabel} conflicted`,
    fallbackDescription: `${actionLabel} could not be completed.`,
    failedTitle: `${actionLabel} failed`,
    invalidRequestTitle: `${actionLabel} rejected`,
    noLeakDescription:
      "The job is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
    noLeakTitle: "Job not found",
    rejectedTitle: `${actionLabel} rejected`,
  });
}

export function useJobLifecycleActions({
  currentStatus,
  jobId,
  projectId,
}: {
  currentStatus: JobStatus | null | undefined;
  jobId: string;
  projectId?: string | null;
}) {
  const apiClient = useApiClient();
  const invalidateQuery = useInvalidateQuery();
  const telemetry = useTelemetry();
  const [feedback, setFeedback] = useState<LifecycleFeedback | null>(null);
  const [pendingAction, setPendingAction] = useState<"cancel" | "confirm-upload" | "retry" | "run" | null>(
    null,
  );

  const refreshViews = useCallback(() => {
    startTransition(() => {
      invalidateQuery(jobDetailQueryKey(jobId));
      invalidateQuery(RECENT_JOBS_QUERY_KEY);
      if (projectId) {
        invalidateQuery(projectJobsQueryKey(projectId));
      }
    });
  }, [invalidateQuery, jobId, projectId]);

  const { polling, startPolling, stopPolling } = useBoundedPolling({
    onPoll: refreshViews,
  });

  useEffect(() => {
    if (!polling.active || polling.watchValue === null || !currentStatus) {
      return;
    }

    if (currentStatus !== polling.watchValue) {
      stopPolling();
    }
  }, [currentStatus, polling.active, polling.watchValue, stopPolling]);

  useEffect(() => {
    if (!polling.reason || !hasPollingAttemptWindowEnded(polling)) {
      return;
    }

    setFeedback(
      createPollingPausedFeedback(
        "Refresh the job detail manually to continue tracking lifecycle changes.",
      ),
    );
  }, [polling]);

  return {
    feedback,
    pendingAction,
    polling,
    async cancelCurrentJob() {
      try {
        setPendingAction("cancel");
        await cancelJob(apiClient, jobId);
        telemetry.track({
          attributes: {
            action: "cancel",
            jobId,
            projectId: projectId ?? undefined,
            result: "succeeded",
            status: currentStatus ?? undefined,
          },
          name: "job.cancel.succeeded",
        });
        setFeedback({
          description: "The job was cancelled. The detail view is refreshing to pick up the terminal status.",
          title: "Cancellation applied",
          tone: "success",
        });
        startPolling({
          reason: "Refreshing cancelled job state",
          watchValue: currentStatus ?? null,
        });
        refreshViews();
      } catch (error) {
        telemetry.track({
          attributes: {
            action: "cancel",
            jobId,
            projectId: projectId ?? undefined,
            result: "failed",
            status: currentStatus ?? undefined,
          },
          error,
          name: "job.cancel.failed",
        });
        setFeedback(describeLifecycleError("Cancel", error));
      } finally {
        setPendingAction(null);
      }
    },
    async confirmUploadByVideoUri(videoUri: string) {
      const normalizedVideoUri = videoUri.trim();
      if (!normalizedVideoUri) {
        setFeedback({
          description: "A non-empty video URI is required for confirm-by-video_uri.",
          title: "Video URI required",
          tone: "warning",
        });
        return;
      }

      try {
        setPendingAction("confirm-upload");
        const result = await confirmJobUpload(apiClient, jobId, { video_uri: normalizedVideoUri });
        telemetry.track({
          attributes: {
            action: "confirm-upload",
            jobId,
            projectId: projectId ?? undefined,
            replayed: result.replayed,
            result: result.replayed ? "replayed" : "succeeded",
            status: result.job.status,
          },
          name: result.replayed
            ? "job.confirm-upload.replayed"
            : "job.confirm-upload.succeeded",
        });
        setFeedback(
          result.replayed
            ? {
                description: "The same video URI was already confirmed for this job. No duplicate mutation was applied.",
                title: "Upload already confirmed",
                tone: "info",
              }
            : {
                description:
                  "The job accepted the confirm-by-video_uri flow and should now refresh into the UPLOADED state view.",
                title: "Upload confirmed",
                tone: "success",
              },
        );
        startPolling({
          reason: "Refreshing upload-confirmed status",
          watchValue: currentStatus ?? null,
        });
        refreshViews();
      } catch (error) {
        telemetry.track({
          attributes: {
            action: "confirm-upload",
            jobId,
            projectId: projectId ?? undefined,
            result: "failed",
            status: currentStatus ?? undefined,
          },
          error,
          name: "job.confirm-upload.failed",
        });
        setFeedback(describeLifecycleError("Confirm upload", error));
      } finally {
        setPendingAction(null);
      }
    },
    dismissFeedback() {
      setFeedback(null);
    },
    isActionPending(action: "cancel" | "confirm-upload" | "retry" | "run") {
      return pendingAction === action;
    },
    async retryFailedJob(modelProfile: string, clientRequestId: string) {
      const normalizedModelProfile = modelProfile.trim();
      const normalizedClientRequestId = clientRequestId.trim();

      if (!normalizedModelProfile || !normalizedClientRequestId) {
        setFeedback({
          description: "Retry requires both model_profile and client_request_id.",
          title: "Retry parameters missing",
          tone: "warning",
        });
        return;
      }

      try {
        setPendingAction("retry");
        const result = await retryJob(apiClient, jobId, {
          client_request_id: normalizedClientRequestId,
          model_profile: normalizedModelProfile,
        });
        telemetry.track({
          attributes: {
            action: "retry",
            dispatchId: result.dispatch_id,
            jobId,
            modelProfile: result.model_profile,
            projectId: projectId ?? undefined,
            replayed: result.replayed,
            result: result.replayed ? "replayed" : "succeeded",
            status: result.status,
          },
          name: result.replayed ? "job.retry.replayed" : "job.retry.succeeded",
        });
        setFeedback(
          result.replayed
            ? {
                description: `Retry replayed existing dispatch ${result.dispatch_id} from ${result.resume_from_status}.`,
                title: "Retry already accepted",
                tone: "info",
              }
            : {
                description: `Retry accepted from ${result.resume_from_status} using checkpoint ${result.checkpoint_ref} and model profile ${result.model_profile}.`,
                title: "Retry dispatched",
                tone: "success",
              },
        );
        startPolling({
          reason: "Watching retry progression",
          watchValue: currentStatus ?? result.status,
        });
        refreshViews();
      } catch (error) {
        telemetry.track({
          attributes: {
            action: "retry",
            jobId,
            modelProfile: normalizedModelProfile,
            projectId: projectId ?? undefined,
            result: "failed",
            status: currentStatus ?? undefined,
          },
          error,
          name: "job.retry.failed",
        });
        setFeedback(describeLifecycleError("Retry", error));
      } finally {
        setPendingAction(null);
      }
    },
    async runWorkflow() {
      try {
        setPendingAction("run");
        const result = await runJob(apiClient, jobId);
        telemetry.track({
          attributes: {
            action: "run",
            dispatchId: result.dispatch_id,
            jobId,
            projectId: projectId ?? undefined,
            replayed: result.replayed,
            result: result.replayed ? "replayed" : "succeeded",
            status: result.status,
          },
          name: result.replayed ? "job.run.replayed" : "job.run.succeeded",
        });
        setFeedback(
          result.replayed
            ? {
                description: `Workflow dispatch ${result.dispatch_id} already exists for this job. Auto-refresh remains active for bounded status checks.`,
                title: "Run already in progress",
                tone: "info",
              }
            : {
                description: `Workflow dispatch ${result.dispatch_id} was accepted. The UI will poll the status a few times to surface progression.`,
                title: "Workflow started",
                tone: "success",
              },
        );
        startPolling({
          reason: "Watching workflow progression",
          watchValue: currentStatus ?? result.status,
        });
        refreshViews();
      } catch (error) {
        telemetry.track({
          attributes: {
            action: "run",
            jobId,
            projectId: projectId ?? undefined,
            result: "failed",
            status: currentStatus ?? undefined,
          },
          error,
          name: "job.run.failed",
        });
        setFeedback(describeLifecycleError("Run workflow", error));
      } finally {
        setPendingAction(null);
      }
    },
    stopPolling,
  };
}
