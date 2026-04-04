import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import type { ApiClient, ApiRequestOptions } from "../../src/shared/api/client";
import {
  cancelJob,
  confirmJobUpload,
  createJob,
  getJob,
  getJobTranscript,
  parseTranscriptNotReadyDetails,
  retryJob,
  runJob,
} from "../../src/features/jobs/api";
import { JobStatusBadge } from "../../src/features/jobs/status";
import { ApiClientError, isNoLeakNotFoundError } from "../../src/shared/api/errors";
import { NoLeakNotFoundState } from "../../src/shared/ui/no-leak-not-found-state";

function createMockApiClient() {
  const calls: Array<{
    body?: ApiRequestOptions["body"];
    method: "get" | "post";
    options?: ApiRequestOptions | Omit<ApiRequestOptions, "method" | "body">;
    path: string;
  }> = [];

  const apiClient: ApiClient = {
    async get<T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">): Promise<T> {
      calls.push({ method: "get", options, path });
      return {
        created_at: "2026-03-24T10:00:00Z",
        id: "job-123",
        project_id: "project-123",
        status: "CREATED",
      } as T;
    },
    async post<T>(
      path: string,
      body?: ApiRequestOptions["body"],
      options?: Omit<ApiRequestOptions, "method" | "body">,
    ): Promise<T> {
      calls.push({ body, method: "post", options, path });
      return {
        created_at: "2026-03-24T10:00:00Z",
        id: "job-123",
        project_id: "project-123",
        status: "CREATED",
      } as T;
    },
    async request<T>(path: string): Promise<T> {
      void path;
      throw new Error("request should not be called directly in job API tests");
    },
  };

  return { apiClient, calls };
}

test("job API uses contract paths and required auth", async () => {
  const { apiClient, calls } = createMockApiClient();

  await createJob(apiClient, "project-123");
  await getJob(apiClient, "job-123");
  await getJobTranscript(apiClient, "job-123", { cursor: "2", limit: 2 });
  await confirmJobUpload(apiClient, "job-123", { video_uri: "gs://bucket/demo.mp4" });
  await runJob(apiClient, "job-123");
  await retryJob(apiClient, "job-123", {
    client_request_id: "retry-123",
    model_profile: "cloud-default",
  });
  await cancelJob(apiClient, "job-123");

  assert.deepEqual(calls, [
    {
      body: null,
      method: "post",
      options: { auth: "required" },
      path: "/projects/project-123/jobs",
    },
    { method: "get", options: { auth: "required" }, path: "/jobs/job-123" },
    {
      method: "get",
      options: { auth: "required" },
      path: "/jobs/job-123/transcript?limit=2&cursor=2",
    },
    {
      body: { video_uri: "gs://bucket/demo.mp4" },
      method: "post",
      options: { auth: "required" },
      path: "/jobs/job-123/confirm-upload",
    },
    {
      body: null,
      method: "post",
      options: { auth: "required" },
      path: "/jobs/job-123/run",
    },
    {
      body: { client_request_id: "retry-123", model_profile: "cloud-default" },
      method: "post",
      options: { auth: "required" },
      path: "/jobs/job-123/retry",
    },
    {
      body: null,
      method: "post",
      options: { auth: "required" },
      path: "/jobs/job-123/cancel",
    },
  ]);
});

test("transcript not-ready details parser only accepts contract shape", () => {
  assert.deepEqual(parseTranscriptNotReadyDetails({ current_status: "TRANSCRIBING" }), {
    current_status: "TRANSCRIBING",
  });
  assert.equal(parseTranscriptNotReadyDetails({ current_status: 42 }), null);
  assert.equal(parseTranscriptNotReadyDetails(null), null);
});

test("no-leak helper only accepts 404 API client errors", () => {
  assert.equal(
    isNoLeakNotFoundError(
      new ApiClientError(404, { code: "RESOURCE_NOT_FOUND", message: "Not found" }),
    ),
    true,
  );
  assert.equal(
    isNoLeakNotFoundError(new ApiClientError(409, { code: "INVALID_STATE", message: "Conflict" })),
    false,
  );
  assert.equal(isNoLeakNotFoundError(new Error("plain error")), false);
});

test("job status badge and generic no-leak state render contract-safe labels", () => {
  const badgeHtml = renderToStaticMarkup(<JobStatusBadge status="DRAFT_READY" />);
  const notFoundHtml = renderToStaticMarkup(
    <NoLeakNotFoundState resourceName="job" returnHref="/jobs" returnLabel="Back to jobs" />,
  );

  assert.match(badgeHtml, /DRAFT_READY/);
  assert.match(notFoundHtml, /job not found/i);
  assert.match(notFoundHtml, /missing or unauthorized job records/i);
  assert.match(notFoundHtml, /Back to jobs/);
});
