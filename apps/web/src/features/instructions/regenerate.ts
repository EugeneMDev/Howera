import { describePollingActivity } from "@/shared/hooks/use-bounded-polling";
import type { FeedbackMessage } from "@/shared/ui/feedback";

import type { RegenerateSelection, RegenerateTask, RegenerateTaskStatus } from "@/features/instructions/api";

export type RegenerateFeedback = FeedbackMessage;

export interface RegeneratePollStatus {
  active: boolean;
  attemptsRemaining: number;
  lastPolledAt: string | null;
  maxAttempts: number;
  reason: string | null;
  startedAt: string | null;
}

export function buildCharRangeSelection(
  startOffset: number | null | undefined,
  endOffset: number | null | undefined,
): RegenerateSelection | null {
  if (
    startOffset === null ||
    startOffset === undefined ||
    endOffset === null ||
    endOffset === undefined ||
    !Number.isInteger(startOffset) ||
    !Number.isInteger(endOffset) ||
    startOffset < 0 ||
    endOffset <= startOffset
  ) {
    return null;
  }

  return {
    char_range: {
      end_offset: endOffset,
      start_offset: startOffset,
    },
  };
}

export function buildBlockIdSelection(blockId: string): RegenerateSelection | null {
  const normalizedBlockId = blockId.trim();
  if (!normalizedBlockId) {
    return null;
  }

  return {
    block_id: normalizedBlockId,
  };
}

export function createRegenerateClientRequestId(): string {
  const suffix =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10);

  return `regen-${suffix}`;
}

export function getRegenerateTaskStatusTone(
  status: RegenerateTaskStatus,
): "danger" | "info" | "success" | "warning" {
  if (status === "SUCCEEDED") {
    return "success";
  }

  if (status === "FAILED") {
    return "danger";
  }

  return "info";
}

export function describeRegenerateTask(task: RegenerateTask): RegenerateFeedback {
  if (task.status === "SUCCEEDED") {
    return {
      description: task.instruction_version
        ? `Regenerate completed and produced instruction version ${task.instruction_version}.`
        : "Regenerate completed successfully.",
      title: task.replayed ? "Existing regenerate result restored" : "Regenerate completed",
      tone: "success",
    };
  }

  if (task.status === "FAILED") {
    return {
      description:
        task.failure_message ??
        "Regenerate task failed. Only sanitized failure details are shown in the workspace.",
      title: task.failure_code ? `Regenerate failed: ${task.failure_code}` : "Regenerate failed",
      tone: "danger",
    };
  }

  return {
    description: task.replayed
      ? "Existing regenerate task restored. Polling continues from its current status."
      : "Regenerate request accepted. Polling has started automatically.",
    title: task.replayed ? "Existing regenerate task restored" : "Regenerate requested",
    tone: "info",
  };
}

export function describeRegeneratePolling(
  polling: RegeneratePollStatus,
): string {
  return describePollingActivity(polling, {
    idleMessage: "Polling is idle.",
  });
}
