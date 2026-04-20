export interface ApiErrorPayload {
  code?: string;
  message?: string;
  details?: unknown;
}

export class ApiClientError extends Error {
  status: number;
  code: string | null;
  details: unknown;

  constructor(status: number, payload?: ApiErrorPayload | null) {
    super(payload?.message ?? `Request failed with status ${status}`);
    this.name = "ApiClientError";
    this.status = status;
    this.code = payload?.code ?? null;
    this.details = payload?.details ?? null;
  }
}

export function isApiClientError(value: unknown): value is ApiClientError {
  return value instanceof ApiClientError;
}

export function isNoLeakNotFoundError(value: unknown): value is ApiClientError {
  return isApiClientError(value) && value.status === 404;
}

export function isApiErrorPayload(value: unknown): value is ApiErrorPayload {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    ("code" in candidate && (typeof candidate.code === "string" || candidate.code === undefined)) ||
    ("message" in candidate && (typeof candidate.message === "string" || candidate.message === undefined))
  );
}
