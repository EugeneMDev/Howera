import { describeCommonApiError } from "@/shared/api/error-feedback";
import type { BoundedPollingState } from "@/shared/hooks/use-bounded-polling";
import { formatDateTime } from "@/shared/lib/format-date";
import type { FeedbackMessage } from "@/shared/ui/feedback";

import type { ExportRecord, ExportStatus } from "@/features/exports/api";

export type ExportFeedback = FeedbackMessage;

export interface ExportDownloadAvailability extends ExportFeedback {
  canDownload: boolean;
  state: "expired" | "failed" | "missing-url" | "pending" | "ready";
}

export function createExportIdempotencyKey(prefix = "export"): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(16).slice(2, 10)}`;
}

export function getExportStatusTone(status: ExportStatus): "danger" | "info" | "success" | "warning" {
  if (status === "SUCCEEDED") {
    return "success";
  }

  if (status === "FAILED") {
    return "danger";
  }

  return status === "RUNNING" ? "warning" : "info";
}

export function describeExportRecord(record: ExportRecord): ExportFeedback {
  if (record.replayed) {
    if (record.status === "SUCCEEDED") {
      return {
        description: `An earlier ${record.format} export request already produced export ${record.id}. This existing record remains the active result for instruction version ${record.instruction_version_id}.`,
        title: "Existing export already ready",
        tone: "success",
      };
    }

    if (record.status === "FAILED") {
      return {
        description: `An earlier ${record.format} export request already failed as export ${record.id}. Re-requesting the same version and format may replay this record until the export inputs change.`,
        title: "Existing failed export restored",
        tone: "warning",
      };
    }

    return {
      description: `An earlier ${record.format} export request already created export ${record.id}. Tracking continues from its current ${record.status.toLowerCase()} state without duplicating workspace history.`,
      title: "Existing export restored",
      tone: "info",
    };
  }

  if (record.status === "REQUESTED") {
    return {
      description: `Export ${record.id} was accepted for instruction version ${record.instruction_version_id}. The workspace will keep polling until the export becomes terminal.`,
      title: "Export requested",
      tone: "info",
    };
  }

  if (record.status === "RUNNING") {
    return {
      description: `Export ${record.id} is running for instruction version ${record.instruction_version_id}. The current editor and job context remain available while processing continues.`,
      title: "Export in progress",
      tone: "warning",
    };
  }

  if (record.status === "SUCCEEDED") {
    return {
      description: `Export ${record.id} succeeded for instruction version ${record.instruction_version_id}. Use Download export or refresh status to fetch a current signed URL in memory only.`,
      title: "Export succeeded",
      tone: "success",
    };
  }

  return {
    description: `Export ${record.id} reached FAILED for instruction version ${record.instruction_version_id}. Request the format again from the current workspace if you need to re-check or replay this export identity.`,
    title: "Export failed",
    tone: "danger",
  };
}

export function describeExportPolling(
  polling: BoundedPollingState,
  pendingExportCount: number,
): string {
  if (polling.active && pendingExportCount > 0) {
    return `Tracking ${pendingExportCount} in-flight export${pendingExportCount === 1 ? "" : "s"} with bounded polling. ${polling.attemptsRemaining} of ${polling.maxAttempts} attempts remaining.`;
  }

  if (pendingExportCount > 0) {
    return `There ${pendingExportCount === 1 ? "is" : "are"} ${pendingExportCount} export${pendingExportCount === 1 ? "" : "s"} still waiting on terminal status. Refresh manually or resume polling after the bounded window.`;
  }

  return "No export polling is currently active.";
}

export function getExportDownloadAvailability(
  record: ExportRecord,
  now = Date.now(),
): ExportDownloadAvailability {
  if (record.status === "FAILED") {
    return {
      canDownload: false,
      description:
        "Download unavailable because this export failed. Request the format again or refresh status after a retry to restore a usable result.",
      state: "failed",
      title: "Download unavailable",
      tone: "danger",
    };
  }

  if (record.status !== "SUCCEEDED") {
    return {
      canDownload: false,
      description:
        "Download becomes available after this export reaches SUCCEEDED. Keep polling or refresh status to fetch a signed URL when processing finishes.",
      state: "pending",
      title: "Download not ready",
      tone: record.status === "RUNNING" ? "warning" : "info",
    };
  }

  if (!record.download_url || !record.download_url_expires_at) {
    return {
      canDownload: false,
      description:
        "Signed download URL is not loaded yet. Download or refresh status to request a current scoped URL for this completed export.",
      state: "missing-url",
      title: "Signed URL unavailable",
      tone: "warning",
    };
  }

  const expiresAt = Date.parse(record.download_url_expires_at);
  if (Number.isFinite(expiresAt) && expiresAt <= now) {
    return {
      canDownload: false,
      description: `The signed download URL expired at ${formatDateTime(record.download_url_expires_at)}. Download again or refresh status to request a new scoped URL.`,
      state: "expired",
      title: "Signed URL expired",
      tone: "warning",
    };
  }

  return {
    canDownload: true,
    description: `Signed URL ready until ${formatDateTime(record.download_url_expires_at)}. It is used immediately from in-memory state and is never persisted in browser storage.`,
    state: "ready",
    title: "Download ready",
    tone: "success",
  };
}

export function describeExportError(
  error: unknown,
  action: "download" | "refresh" | "request",
): ExportFeedback {
  return describeCommonApiError(error, {
    actionLabel:
      action === "request"
        ? "Export request"
        : action === "refresh"
          ? "Export refresh"
          : "Export download",
    conflictTitle: action === "download" ? "Export download unavailable" : undefined,
    fallbackDescription:
      action === "request"
        ? "The export request could not be accepted."
        : action === "refresh"
          ? "The export status could not be refreshed."
          : "The export download could not be prepared.",
    failedTitle:
      action === "request"
        ? "Export request failed"
        : action === "refresh"
          ? "Export refresh failed"
          : "Export download failed",
    invalidRequestTitle:
      action === "request"
        ? "Export request rejected"
        : action === "refresh"
          ? "Export refresh rejected"
          : "Export download unavailable",
    noLeakDescription:
      "The export context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
    noLeakTitle: "Export context unavailable",
    rejectedTitle:
      action === "request"
        ? "Export request rejected"
        : action === "refresh"
          ? "Export refresh rejected"
          : "Export download unavailable",
  });
}
