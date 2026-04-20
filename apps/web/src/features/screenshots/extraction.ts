import type { BoundedPollingState } from "@/shared/hooks/use-bounded-polling";
import { describePollingActivity } from "@/shared/hooks/use-bounded-polling";
import type { FeedbackMessage } from "@/shared/ui/feedback";

import type {
  ScreenshotCharRange,
  ScreenshotOperation,
  ScreenshotTask,
  ScreenshotTaskStatus,
} from "@/features/screenshots/api";

export type ScreenshotFeedback = FeedbackMessage;

export function buildScreenshotCharRange(
  start?: number | null,
  end?: number | null,
): ScreenshotCharRange | null {
  if (
    typeof start !== "number" ||
    typeof end !== "number" ||
    !Number.isInteger(start) ||
    !Number.isInteger(end) ||
    start < 0 ||
    end <= start
  ) {
    return null;
  }

  return {
    end_offset: end,
    start_offset: start,
  };
}

export function normalizeScreenshotBlockId(blockId: string): string | null {
  const normalizedBlockId = blockId.trim();
  return normalizedBlockId.length > 0 ? normalizedBlockId : null;
}

export function createScreenshotIdempotencyKey(prefix = "screenshot"): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(16).slice(2, 10)}`;
}

function getScreenshotOperationLabel(operation: ScreenshotOperation): string {
  return operation === "replace" ? "Screenshot replacement" : "Screenshot extraction";
}

export function describeScreenshotTask(task: ScreenshotTask): ScreenshotFeedback {
  const operationLabel = getScreenshotOperationLabel(task.operation);

  if (task.replayed) {
    return {
      description:
        task.operation === "replace"
          ? "An earlier replacement request already created this screenshot task. Tracking continues from its current status without duplicating UI state."
          : "An earlier extraction request already created this screenshot task. Tracking continues from its current status without duplicating UI state.",
      title: task.operation === "replace" ? "Existing replacement task restored" : "Existing screenshot task restored",
      tone: "info",
    };
  }

  if (task.status === "SUCCEEDED") {
    if (task.anchor_id && task.asset_id) {
      return {
        description:
          task.operation === "replace"
            ? `Screenshot replacement completed and linked anchor ${task.anchor_id} to asset ${task.asset_id}.`
            : `Screenshot extraction completed and linked anchor ${task.anchor_id} to asset ${task.asset_id}.`,
        title: task.operation === "replace" ? "Screenshot replaced" : "Screenshot extracted",
        tone: "success",
      };
    }

    if (task.anchor_id) {
      return {
        description: `${operationLabel} completed and resolved anchor ${task.anchor_id}.`,
        title: task.operation === "replace" ? "Screenshot replaced" : "Screenshot extracted",
        tone: "success",
      };
    }

    if (task.asset_id) {
      return {
        description: `${operationLabel} completed and produced asset ${task.asset_id}.`,
        title: task.operation === "replace" ? "Screenshot replaced" : "Screenshot extracted",
        tone: "success",
      };
    }

    return {
      description: `${operationLabel} completed successfully.`,
      title: task.operation === "replace" ? "Screenshot replaced" : "Screenshot extracted",
      tone: "success",
    };
  }

  if (task.status === "FAILED") {
    return {
      description: task.failure_message || `${operationLabel} failed.`,
      title: task.failure_code
        ? `${operationLabel} failed: ${task.failure_code}`
        : `${operationLabel} failed`,
      tone: "danger",
    };
  }

  if (task.status === "RUNNING") {
    return {
      description:
        task.operation === "replace"
          ? "Screenshot replacement is running. Polling will keep this panel current until the task reaches a terminal state or the bounded refresh window ends."
          : "Screenshot extraction is running. Polling will keep this panel current until the task reaches a terminal state or the bounded refresh window ends.",
      title: task.operation === "replace" ? "Screenshot replacement running" : "Screenshot extraction running",
      tone: "info",
    };
  }

  return {
    description:
      task.operation === "replace"
        ? "Screenshot replacement was accepted and is waiting to run. Polling starts automatically so the editor can stay in place while the task progresses."
        : "Screenshot extraction was accepted and is waiting to run. Polling starts automatically so the editor can stay in place while the task progresses.",
    title: task.operation === "replace" ? "Replacement request accepted" : "Screenshot request accepted",
    tone: "info",
  };
}

export function describeScreenshotPolling(
  polling: Pick<BoundedPollingState, "active" | "attemptsRemaining" | "maxAttempts">,
): string {
  return describePollingActivity({
    ...polling,
    startedAt: polling.active ? "active" : "completed",
  });
}

export function getScreenshotTaskStatusTone(status: ScreenshotTaskStatus): "danger" | "info" | "success" {
  if (status === "SUCCEEDED") {
    return "success";
  }

  if (status === "FAILED") {
    return "danger";
  }

  return "info";
}
