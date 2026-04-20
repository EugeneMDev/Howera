import {
  ApiClientError,
  isNoLeakNotFoundError,
  type ApiErrorPayload,
} from "@/shared/api/errors";
import type { FeedbackMessage } from "@/shared/ui/feedback";

interface CommonApiErrorOptions {
  actionLabel: string;
  fallbackDescription: string;
  noLeakDescription: string;
  noLeakTitle: string;
  conflictDescription?: string;
  conflictTitle?: string;
  failedTitle?: string;
  invalidRequestDescription?: string;
  invalidRequestTitle?: string;
  rejectedTitle?: string;
  unauthorizedDescription?: string;
  unauthorizedTitle?: string;
  upstreamDescription?: string;
  upstreamTitle?: string;
}

function getErrorMessage(error: ApiClientError, fallback: string): string {
  return error.message || fallback;
}

function getApiErrorDetails(error: ApiClientError): ApiErrorPayload["details"] | null {
  return error.details ?? null;
}

export function toUserSafeErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

export function describeCommonApiError(
  error: unknown,
  {
    actionLabel,
    fallbackDescription,
    noLeakDescription,
    noLeakTitle,
    conflictDescription,
    conflictTitle = `${actionLabel} conflicted`,
    failedTitle = `${actionLabel} failed`,
    invalidRequestDescription,
    invalidRequestTitle = `${actionLabel} rejected`,
    rejectedTitle = `${actionLabel} rejected`,
    unauthorizedDescription = "Your session expired or was rejected by the API. Sign in again.",
    unauthorizedTitle = "Session unavailable",
    upstreamDescription = "The API could not complete the request because an upstream dependency failed.",
    upstreamTitle = failedTitle,
  }: CommonApiErrorOptions,
): FeedbackMessage {
  if (isNoLeakNotFoundError(error)) {
    return {
      description: noLeakDescription,
      title: noLeakTitle,
      tone: "danger",
    };
  }

  if (!(error instanceof ApiClientError)) {
    return {
      description: toUserSafeErrorMessage(error, fallbackDescription),
      title: failedTitle,
      tone: "danger",
    };
  }

  switch (error.status) {
    case 400:
      return {
        description: getErrorMessage(error, invalidRequestDescription ?? fallbackDescription),
        title: invalidRequestTitle,
        tone: "warning",
      };
    case 401:
      return {
        description: unauthorizedDescription,
        title: unauthorizedTitle,
        tone: "warning",
      };
    case 409:
      return {
        description: getErrorMessage(error, conflictDescription ?? fallbackDescription),
        title: conflictTitle,
        tone: "warning",
      };
    case 502:
      return {
        description: getErrorMessage(error, upstreamDescription),
        title: upstreamTitle,
        tone: "danger",
      };
    default:
      if (error.status >= 500) {
        return {
          description: getErrorMessage(error, fallbackDescription),
          title: failedTitle,
          tone: "danger",
        };
      }

      return {
        description: getErrorMessage(error, fallbackDescription),
        title: rejectedTitle,
        tone: "warning",
      };
  }
}

export function getApiErrorDetailsRecord(
  error: unknown,
): Record<string, unknown> | null {
  if (!(error instanceof ApiClientError)) {
    return null;
  }

  const details = getApiErrorDetails(error);
  if (typeof details !== "object" || details === null) {
    return null;
  }

  return details as Record<string, unknown>;
}
