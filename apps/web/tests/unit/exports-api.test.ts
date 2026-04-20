import assert from "node:assert/strict";
import test from "node:test";

import type { ApiClient, ApiRequestOptions, ApiResponse } from "../../src/shared/api/client";
import { getExport, requestExport, type ExportRecord } from "../../src/features/exports/api";

function createMockApiClient() {
  const calls: Array<{
    method: "get" | "request" | "requestWithMeta";
    options?: ApiRequestOptions | Omit<ApiRequestOptions, "method" | "body">;
    path: string;
  }> = [];

  const acceptedExport: ExportRecord = {
    created_at: "2026-03-27T10:00:00Z",
    format: "PDF",
    id: "export-pdf-123",
    identity_key: "identity-pdf-123",
    instruction_version_id: "7",
    job_id: "job-123",
    screenshot_set_hash: "hash-pdf-123",
    status: "REQUESTED",
    updated_at: "2026-03-27T10:00:00Z",
  };
  const replayedExport: ExportRecord = {
    created_at: "2026-03-27T10:01:00Z",
    format: "MD_ZIP",
    id: "export-md-123",
    identity_key: "identity-md-123",
    instruction_version_id: "7",
    job_id: "job-123",
    screenshot_set_hash: "hash-md-123",
    status: "SUCCEEDED",
    updated_at: "2026-03-27T10:05:00Z",
  };

  const apiClient: ApiClient = {
    async get<T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">): Promise<T> {
      calls.push({ method: "get", options, path });
      return replayedExport as T;
    },
    async post<T>(): Promise<T> {
      throw new Error("post should not be called directly in export API tests");
    },
    async request<T>(path: string, options?: ApiRequestOptions): Promise<T> {
      calls.push({ method: "request", options, path });
      return acceptedExport as T;
    },
    async requestWithMeta<T>(path: string, options?: ApiRequestOptions): Promise<ApiResponse<T>> {
      calls.push({ method: "requestWithMeta", options, path });
      const format = (options?.body as { format?: string } | undefined)?.format;

      return {
        data: (format === "MD_ZIP" ? replayedExport : acceptedExport) as T,
        headers: new Headers(),
        status: format === "MD_ZIP" ? 200 : 202,
      };
    },
  };

  return { acceptedExport, apiClient, calls, replayedExport };
}

test("export API uses contract paths and exposes accepted vs replayed responses", async () => {
  const { acceptedExport, apiClient, calls, replayedExport } = createMockApiClient();

  const accepted = await requestExport(apiClient, "job-123", {
    format: "PDF",
    idempotency_key: "export-pdf-123",
    instruction_version_id: "7",
  });
  const replayed = await requestExport(apiClient, "job-123", {
    format: "MD_ZIP",
    idempotency_key: "export-md-123",
    instruction_version_id: "7",
  });
  const loaded = await getExport(apiClient, "export-md-123");

  assert.deepEqual(calls, [
    {
      method: "requestWithMeta",
      options: {
        auth: "required",
        body: {
          format: "PDF",
          idempotency_key: "export-pdf-123",
          instruction_version_id: "7",
        },
        method: "POST",
      },
      path: "/jobs/job-123/exports",
    },
    {
      method: "requestWithMeta",
      options: {
        auth: "required",
        body: {
          format: "MD_ZIP",
          idempotency_key: "export-md-123",
          instruction_version_id: "7",
        },
        method: "POST",
      },
      path: "/jobs/job-123/exports",
    },
    {
      method: "get",
      options: { auth: "required" },
      path: "/exports/export-md-123",
    },
  ]);

  assert.deepEqual(accepted, {
    ...acceptedExport,
    replayed: false,
  });
  assert.deepEqual(replayed, {
    ...replayedExport,
    replayed: true,
  });
  assert.equal(loaded.id, "export-md-123");
  assert.equal(loaded.status, "SUCCEEDED");
});
