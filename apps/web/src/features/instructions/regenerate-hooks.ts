"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { describeCommonApiError } from "@/shared/api/error-feedback";
import { ApiClientError } from "@/shared/api/errors";
import {
  createPollingPausedFeedback,
  hasPollingAttemptWindowEnded,
  useBoundedPolling,
} from "@/shared/hooks/use-bounded-polling";
import { useApiClient, useTelemetry } from "@/shared/providers/app-providers";
import {
  getRegenerateTask,
  isRegenerateTaskTerminal,
  parseVersionConflictDetails,
  requestInstructionRegenerate,
  type RegenerateRequestInput,
  type RegenerateTask,
} from "@/features/instructions/api";
import { describeRegenerateTask, type RegenerateFeedback } from "@/features/instructions/regenerate";

function describeRegenerateRequestError(error: unknown): RegenerateFeedback {
  if (error instanceof ApiClientError && error.status === 409 && error.code === "VERSION_CONFLICT") {
    const details = parseVersionConflictDetails(error.details);

    return {
      description:
        details === null
          ? "The regenerate request used a stale instruction base version. Reload the latest instruction before trying again."
          : `The regenerate request was based on version ${details.base_version}, but the server is already on version ${details.current_version}. Reload the latest instruction before trying again.`,
      title: "Regenerate blocked by version conflict",
      tone: "warning",
    };
  }

  return describeCommonApiError(error, {
    actionLabel: "Regenerate request",
    conflictTitle: "Regenerate request conflicted",
    fallbackDescription: "Regenerate request could not be created.",
    failedTitle: "Regenerate request failed",
    invalidRequestTitle: "Regenerate request rejected",
    noLeakDescription:
      "The instruction is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
    noLeakTitle: "Instruction unavailable",
    rejectedTitle: "Regenerate request rejected",
  });
}

function describeRegenerateRefreshError(error: unknown): RegenerateFeedback {
  return describeCommonApiError(error, {
    actionLabel: "Task refresh",
    fallbackDescription: "Regenerate task status could not be refreshed.",
    failedTitle: "Task refresh failed",
    invalidRequestTitle: "Task refresh rejected",
    noLeakDescription:
      "The instruction is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
    noLeakTitle: "Instruction unavailable",
    rejectedTitle: "Task refresh rejected",
  });
}

interface UseInstructionRegenerateOptions {
  instructionId: string;
  onTaskSucceeded?: (task: RegenerateTask) => void;
  onVersionConflict?: () => void;
}

export function useInstructionRegenerate({
  instructionId,
  onTaskSucceeded,
  onVersionConflict,
}: UseInstructionRegenerateOptions) {
  const apiClient = useApiClient();
  const telemetry = useTelemetry();
  const [task, setTask] = useState<RegenerateTask | null>(null);
  const [feedback, setFeedback] = useState<RegenerateFeedback | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastClientRequestId, setLastClientRequestId] = useState<string | null>(null);
  const succeededTaskIdsRef = useRef<Set<string>>(new Set());
  const reportedTerminalTaskIdsRef = useRef<Set<string>>(new Set());
  const onTaskSucceededRef = useRef(onTaskSucceeded);
  const onVersionConflictRef = useRef(onVersionConflict);

  onTaskSucceededRef.current = onTaskSucceeded;
  onVersionConflictRef.current = onVersionConflict;

  const reportTerminalTask = useCallback(
    (nextTask: RegenerateTask) => {
      setFeedback(describeRegenerateTask(nextTask));

      if (!reportedTerminalTaskIdsRef.current.has(nextTask.id)) {
        reportedTerminalTaskIdsRef.current.add(nextTask.id);
        telemetry.track({
          attributes: {
            action: "regenerate",
            instructionId,
            result: nextTask.status === "SUCCEEDED" ? "succeeded" : "failed",
            status: nextTask.status,
            taskId: nextTask.id,
          },
          name:
            nextTask.status === "SUCCEEDED"
              ? "instruction.regenerate.succeeded"
              : "instruction.regenerate.failed",
        });
      }

      if (nextTask.status === "SUCCEEDED" && !succeededTaskIdsRef.current.has(nextTask.id)) {
        succeededTaskIdsRef.current.add(nextTask.id);
        onTaskSucceededRef.current?.(nextTask);
      }
    },
    [instructionId, telemetry],
  );

  const refreshTask = useCallback(
    async (taskId: string) => {
      const nextTask = await getRegenerateTask(apiClient, taskId);
      setTask(nextTask);

      if (isRegenerateTaskTerminal(nextTask.status)) {
        reportTerminalTask(nextTask);
      }

      return nextTask;
    },
    [apiClient, reportTerminalTask],
  );

  const { polling, startPolling, stopPolling } = useBoundedPolling({
    onPoll: () => {
      if (!task?.id) {
        return;
      }

      void refreshTask(task.id)
        .then((nextTask) => {
          if (isRegenerateTaskTerminal(nextTask.status)) {
            stopPolling();
          }
        })
        .catch((error) => {
          setFeedback(describeRegenerateRefreshError(error));
          stopPolling();
        });
    },
  });

  useEffect(() => {
    if (hasPollingAttemptWindowEnded(polling) && task !== null) {
      setFeedback(
        createPollingPausedFeedback(
          "Refresh task status manually to continue tracking this regenerate request.",
        ),
      );
    }
  }, [polling, task]);

  useEffect(() => {
    setTask(null);
    setFeedback(null);
    setIsSubmitting(false);
    setLastClientRequestId(null);
    reportedTerminalTaskIdsRef.current.clear();
    stopPolling();
  }, [instructionId, stopPolling]);

  return {
    feedback,
    isSubmitting,
    lastClientRequestId,
    polling,
    task,
    async refreshCurrentTask(): Promise<void> {
      if (!task?.id) {
        return;
      }

      try {
        const nextTask = await refreshTask(task.id);
        if (isRegenerateTaskTerminal(nextTask.status)) {
          stopPolling();
        }
      } catch (error) {
        setFeedback(describeRegenerateRefreshError(error));
      }
    },
    async submit(input: RegenerateRequestInput): Promise<void> {
      try {
        setIsSubmitting(true);
        setFeedback(null);
        setLastClientRequestId(input.client_request_id);
        const nextTask = await requestInstructionRegenerate(apiClient, instructionId, input);
        setTask(nextTask);
        telemetry.track({
          attributes: {
            action: "regenerate",
            instructionId,
            replayed: nextTask.replayed ?? false,
            result: nextTask.replayed ? "replayed" : "requested",
            status: nextTask.status,
            taskId: nextTask.id,
          },
          name: nextTask.replayed
            ? "instruction.regenerate.replayed"
            : "instruction.regenerate.requested",
        });

        if (isRegenerateTaskTerminal(nextTask.status)) {
          stopPolling();
          reportTerminalTask(nextTask);
          return;
        }

        setFeedback(describeRegenerateTask(nextTask));
        startPolling({
          intervalMs: 2500,
          maxAttempts: 8,
          reason: "regenerate-task-status",
          watchValue: nextTask.id,
        });
      } catch (error) {
        const nextFeedback = describeRegenerateRequestError(error);
        setFeedback(nextFeedback);
        telemetry.track({
          attributes: {
            action: "regenerate",
            instructionId,
            result: "failed",
          },
          error,
          name: "instruction.regenerate.request-failed",
        });
        if (
          error instanceof ApiClientError &&
          error.status === 409 &&
          error.code === "VERSION_CONFLICT"
        ) {
          onVersionConflictRef.current?.();
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    dismissFeedback() {
      setFeedback(null);
    },
    stopPolling,
  };
}
