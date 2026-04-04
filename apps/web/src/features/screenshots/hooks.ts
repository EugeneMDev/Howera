"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { describeCommonApiError } from "@/shared/api/error-feedback";
import {
  createPollingPausedFeedback,
  hasPollingAttemptWindowEnded,
  useBoundedPolling,
} from "@/shared/hooks/use-bounded-polling";
import { useApiClient, useTelemetry } from "@/shared/providers/app-providers";
import {
  getScreenshotTask,
  isScreenshotTaskTerminal,
  requestScreenshotExtraction,
  type ScreenshotExtractionRequestInput,
  type ScreenshotTask,
} from "@/features/screenshots/api";
import {
  describeScreenshotTask,
  type ScreenshotFeedback,
} from "@/features/screenshots/extraction";

function describeScreenshotRequestError(error: unknown): ScreenshotFeedback {
  return describeCommonApiError(error, {
    actionLabel: "Screenshot request",
    fallbackDescription: "Screenshot extraction could not be requested.",
    failedTitle: "Screenshot request failed",
    invalidRequestTitle: "Screenshot request rejected",
    noLeakDescription:
      "The job or instruction context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
    noLeakTitle: "Screenshot context unavailable",
    rejectedTitle: "Screenshot request rejected",
  });
}

function describeScreenshotRefreshError(error: unknown): ScreenshotFeedback {
  return describeCommonApiError(error, {
    actionLabel: "Task refresh",
    fallbackDescription: "Screenshot task status could not be refreshed.",
    failedTitle: "Task refresh failed",
    invalidRequestTitle: "Task refresh rejected",
    noLeakDescription:
      "The job or instruction context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
    noLeakTitle: "Screenshot context unavailable",
    rejectedTitle: "Task refresh rejected",
  });
}

export function useScreenshotExtraction(scopeKey: string, jobId: string) {
  const apiClient = useApiClient();
  const telemetry = useTelemetry();
  const [task, setTask] = useState<ScreenshotTask | null>(null);
  const [feedback, setFeedback] = useState<ScreenshotFeedback | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastIdempotencyKey, setLastIdempotencyKey] = useState<string | null>(null);
  const reportedTerminalTaskIdsRef = useRef<Set<string>>(new Set());

  const reportTerminalTask = useCallback(
    (nextTask: ScreenshotTask) => {
      setFeedback(describeScreenshotTask(nextTask));

      if (!reportedTerminalTaskIdsRef.current.has(nextTask.task_id)) {
        reportedTerminalTaskIdsRef.current.add(nextTask.task_id);
        telemetry.track({
          attributes: {
            action: "extract",
            anchorId: nextTask.anchor_id ?? undefined,
            assetId: nextTask.asset_id ?? undefined,
            jobId,
            result: nextTask.status === "SUCCEEDED" ? "succeeded" : "failed",
            status: nextTask.status,
            taskId: nextTask.task_id,
          },
          name:
            nextTask.status === "SUCCEEDED"
              ? "screenshot.extract.succeeded"
              : "screenshot.extract.failed",
        });
      }
    },
    [jobId, telemetry],
  );

  const refreshTask = useCallback(
    async (taskId: string) => {
      const nextTask = await getScreenshotTask(apiClient, taskId);
      setTask((current) => ({
        ...nextTask,
        replayed: current?.replayed && current.task_id === nextTask.task_id ? current.replayed : nextTask.replayed,
      }));

      if (isScreenshotTaskTerminal(nextTask.status)) {
        reportTerminalTask(nextTask);
      }

      return nextTask;
    },
    [apiClient, reportTerminalTask],
  );

  const { polling, startPolling, stopPolling } = useBoundedPolling({
    onPoll: () => {
      if (!task?.task_id) {
        return;
      }

      void refreshTask(task.task_id)
        .then((nextTask) => {
          if (isScreenshotTaskTerminal(nextTask.status)) {
            stopPolling();
          }
        })
        .catch((error) => {
          setFeedback(describeScreenshotRefreshError(error));
          stopPolling();
        });
    },
  });

  useEffect(() => {
    if (hasPollingAttemptWindowEnded(polling) && task !== null) {
      setFeedback(
        createPollingPausedFeedback(
          "Refresh task status manually to continue tracking this screenshot extraction.",
        ),
      );
    }
  }, [polling, task]);

  useEffect(() => {
    setTask(null);
    setFeedback(null);
    setIsSubmitting(false);
    setLastIdempotencyKey(null);
    reportedTerminalTaskIdsRef.current.clear();
    stopPolling();
  }, [scopeKey, stopPolling]);

  return {
    feedback,
    isSubmitting,
    lastIdempotencyKey,
    polling,
    task,
    async refreshCurrentTask(): Promise<void> {
      if (!task?.task_id) {
        return;
      }

      try {
        const nextTask = await refreshTask(task.task_id);
        if (isScreenshotTaskTerminal(nextTask.status)) {
          stopPolling();
        }
      } catch (error) {
        setFeedback(describeScreenshotRefreshError(error));
      }
    },
    async submit(input: ScreenshotExtractionRequestInput): Promise<void> {
      try {
        setIsSubmitting(true);
        setFeedback(null);
        setLastIdempotencyKey(input.idempotency_key ?? null);

        const previousTaskId = task?.task_id ?? null;
        const nextTask = await requestScreenshotExtraction(apiClient, jobId, input);
        const normalizedTask =
          previousTaskId !== null && previousTaskId === nextTask.task_id
            ? { ...nextTask, replayed: true }
            : nextTask;

        setTask(normalizedTask);
        telemetry.track({
          attributes: {
            action: "extract",
            jobId,
            replayed: normalizedTask.replayed ?? false,
            result: normalizedTask.replayed ? "replayed" : "requested",
            status: normalizedTask.status,
            taskId: normalizedTask.task_id,
          },
          name: normalizedTask.replayed
            ? "screenshot.extract.replayed"
            : "screenshot.extract.requested",
        });

        if (isScreenshotTaskTerminal(normalizedTask.status)) {
          stopPolling();
          reportTerminalTask(normalizedTask);
          return;
        }

        setFeedback(describeScreenshotTask(normalizedTask));
        startPolling({
          intervalMs: 2500,
          maxAttempts: 10,
          reason: "screenshot-task-status",
          watchValue: normalizedTask.task_id,
        });
      } catch (error) {
        telemetry.track({
          attributes: {
            action: "extract",
            jobId,
            result: "failed",
          },
          error,
          name: "screenshot.extract.request-failed",
        });
        setFeedback(describeScreenshotRequestError(error));
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
