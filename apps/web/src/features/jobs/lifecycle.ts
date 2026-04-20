import type { Job, JobStatus } from "@/features/jobs/api";

export const DEFAULT_RETRY_MODEL_PROFILE = "cloud-default";

export const PRIMARY_LIFECYCLE_STATUSES: JobStatus[] = [
  "CREATED",
  "UPLOADING",
  "UPLOADED",
  "AUDIO_EXTRACTING",
  "AUDIO_READY",
  "TRANSCRIBING",
  "TRANSCRIPT_READY",
  "GENERATING",
  "DRAFT_READY",
  "EDITING",
  "REGENERATING",
  "EXPORTING",
  "DONE",
];

export const TERMINAL_LIFECYCLE_STATUSES: JobStatus[] = ["FAILED", "CANCELLED"];

export interface JobLifecycleActionAvailability {
  canCancel: boolean;
  canConfirmUpload: boolean;
  canRetry: boolean;
  canRun: boolean;
}

export type JobLifecyclePendingAction = "cancel" | "confirm-upload" | "retry" | "run" | null;

export interface JobLifecycleActionDisabledState {
  cancelDisabled: boolean;
  confirmUploadDisabled: boolean;
  inputDisabled: boolean;
  retryDisabled: boolean;
  runDisabled: boolean;
}

export function createClientRequestId(prefix = "retry"): string {
  const randomPart =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;

  return `${prefix}-${randomPart}`;
}

export function getJobLifecycleActionAvailability(
  job: Pick<Job, "status">,
): JobLifecycleActionAvailability {
  return {
    canCancel: !["FAILED", "CANCELLED", "DONE"].includes(job.status),
    canConfirmUpload: job.status === "CREATED" || job.status === "UPLOADING",
    canRetry: job.status === "FAILED",
    canRun: job.status === "UPLOADED",
  };
}

export function getJobLifecycleActionDisabledState(
  availability: JobLifecycleActionAvailability,
  pendingAction: JobLifecyclePendingAction,
): JobLifecycleActionDisabledState {
  const isLocked = pendingAction !== null;

  return {
    cancelDisabled: !availability.canCancel || isLocked,
    confirmUploadDisabled: !availability.canConfirmUpload || isLocked,
    inputDisabled: isLocked,
    retryDisabled: !availability.canRetry || isLocked,
    runDisabled: !availability.canRun || isLocked,
  };
}

export function getLifecycleTimelineState(
  timelineStatus: JobStatus,
  currentStatus: JobStatus,
): "completed" | "current" | "pending" {
  if (timelineStatus === currentStatus) {
    return "current";
  }

  if (timelineStatus === "CREATED" && currentStatus !== "CREATED") {
    return "completed";
  }

  if (TERMINAL_LIFECYCLE_STATUSES.includes(currentStatus)) {
    return "pending";
  }

  const currentIndex = PRIMARY_LIFECYCLE_STATUSES.indexOf(currentStatus);
  const timelineIndex = PRIMARY_LIFECYCLE_STATUSES.indexOf(timelineStatus);

  if (currentIndex > -1 && timelineIndex > -1 && timelineIndex < currentIndex) {
    return "completed";
  }

  return "pending";
}
