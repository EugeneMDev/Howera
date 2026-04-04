import { isApiClientError } from "@/shared/api/errors";
import type { PublicAuthProvider } from "@/shared/config/runtime";

const REDACTED_VALUE = "[redacted]";

const ALLOWED_ATTRIBUTE_KEYS = [
  "action",
  "anchorId",
  "appEnv",
  "assetId",
  "authProvider",
  "dispatchId",
  "errorCode",
  "exportId",
  "format",
  "hostingTarget",
  "httpStatus",
  "instructionId",
  "instructionVersion",
  "instructionVersionId",
  "jobId",
  "modelProfile",
  "projectId",
  "reason",
  "replayed",
  "result",
  "status",
  "taskId",
  "uploadId",
  "versionConflict",
] as const;

export type SafeTelemetryAttributeKey = (typeof ALLOWED_ATTRIBUTE_KEYS)[number];

export type SafeTelemetryAttributeValue = boolean | number | string;

export type SafeTelemetryAttributes = Partial<
  Record<SafeTelemetryAttributeKey, SafeTelemetryAttributeValue>
>;

export interface TelemetryDefaults {
  appEnv: string;
  authProvider: PublicAuthProvider;
  hostingTarget: string;
}

export interface SafeTelemetryRecord {
  attributes: SafeTelemetryAttributes;
  name: string;
  occurredAt: string;
}

export interface TelemetryEventInput {
  attributes?: Record<string, unknown>;
  error?: unknown;
  name: string;
}

export interface TelemetryClient {
  track: (event: TelemetryEventInput) => void;
}

function sanitizeTelemetryString(value: string): string {
  const normalized = value.trim();
  if (normalized.length === 0) {
    return normalized;
  }

  if (
    normalized.includes("\n") ||
    normalized.length > 120 ||
    /^bearer\s+/i.test(normalized) ||
    /^test:[^:]+:/i.test(normalized) ||
    /^https?:\/\//i.test(normalized) ||
    /^gs:\/\//i.test(normalized) ||
    /x-amz-signature=|sig=|token=|signature=/i.test(normalized)
  ) {
    return REDACTED_VALUE;
  }

  return normalized;
}

function toSafeTelemetryValue(value: unknown): SafeTelemetryAttributeValue | null {
  if (typeof value === "boolean" || typeof value === "number") {
    return value;
  }

  if (typeof value === "string") {
    return sanitizeTelemetryString(value);
  }

  return null;
}

export function sanitizeTelemetryAttributes(
  attributes: Record<string, unknown> = {},
): SafeTelemetryAttributes {
  const sanitized: SafeTelemetryAttributes = {};

  for (const key of ALLOWED_ATTRIBUTE_KEYS) {
    if (!(key in attributes)) {
      continue;
    }

    const safeValue = toSafeTelemetryValue(attributes[key]);
    if (safeValue !== null) {
      sanitized[key] = safeValue;
    }
  }

  return sanitized;
}

function extractTelemetryErrorAttributes(error: unknown): SafeTelemetryAttributes {
  if (isApiClientError(error)) {
    return {
      errorCode: sanitizeTelemetryString(error.code ?? "API_CLIENT_ERROR"),
      httpStatus: error.status,
    };
  }

  if (error instanceof Error) {
    return {
      errorCode: sanitizeTelemetryString(error.name || "ERROR"),
    };
  }

  return {};
}

export function sanitizeTelemetryEvent(
  event: TelemetryEventInput,
  defaults: TelemetryDefaults,
): SafeTelemetryRecord {
  const occurredAt = new Date().toISOString();

  return {
    attributes: {
      ...sanitizeTelemetryAttributes({
        appEnv: defaults.appEnv,
        authProvider: defaults.authProvider,
        hostingTarget: defaults.hostingTarget,
      }),
      ...sanitizeTelemetryAttributes(event.attributes),
      ...extractTelemetryErrorAttributes(event.error),
    },
    name: sanitizeTelemetryString(event.name),
    occurredAt,
  };
}

export function createConsoleTelemetryEmitter(
  logger: (message?: unknown, ...optionalParams: unknown[]) => void = console.info,
): (record: SafeTelemetryRecord) => void {
  return (record) => {
    logger("[howera-telemetry]", record);
  };
}

export function createTelemetryClient({
  defaults,
  emit,
  enabled = false,
}: {
  defaults: TelemetryDefaults;
  emit?: (record: SafeTelemetryRecord) => void;
  enabled?: boolean;
}): TelemetryClient {
  return {
    track(event: TelemetryEventInput) {
      if (!enabled) {
        return;
      }

      const record = sanitizeTelemetryEvent(event, defaults);
      emit?.(record);
    },
  };
}
