import assert from "node:assert/strict";
import test from "node:test";

import { createApiClient } from "../../src/shared/api/client";
import { ApiClientError } from "../../src/shared/api/errors";

test("api client injects bearer token for authenticated requests", async (t) => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const originalFetch = globalThis.fetch;

  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    calls.push({ input, init });
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const client = createApiClient({
    baseUrl: "http://localhost:8000/api/v1",
    getAccessToken: async () => "firebase-token",
  });

  const response = await client.get<{ ok: boolean }>("/projects", { auth: "required" });

  assert.deepEqual(response, { ok: true });
  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, "http://localhost:8000/api/v1/projects");
  const headers = new Headers(calls[0]?.init?.headers);
  assert.equal(headers.get("Authorization"), "Bearer firebase-token");
});

test("api client rejects required auth requests when no token exists", async () => {
  const client = createApiClient({
    baseUrl: "http://localhost:8000/api/v1",
    getAccessToken: async () => null,
  });

  await assert.rejects(
    client.get("/projects", { auth: "required" }),
    (error: unknown) =>
      error instanceof ApiClientError &&
      error.status === 401 &&
      error.code === "UNAUTHORIZED" &&
      error.message === "Missing access token",
  );
});

test("api client delegates 401 recovery before rethrowing unauthorized errors", async (t) => {
  const unauthorizedErrors: ApiClientError[] = [];
  const originalFetch = globalThis.fetch;

  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (): Promise<Response> =>
    new Response(
      JSON.stringify({
        code: "UNAUTHORIZED",
        message: "Expired Firebase session",
      }),
      {
        status: 401,
        statusText: "Unauthorized",
        headers: { "Content-Type": "application/json" },
      },
    );

  const client = createApiClient({
    baseUrl: "http://localhost:8000/api/v1",
    getAccessToken: async () => "expired-token",
    onUnauthorized: (error) => {
      unauthorizedErrors.push(error);
    },
  });

  await assert.rejects(
    client.get("/projects", { auth: "required" }),
    (error: unknown) =>
      error instanceof ApiClientError &&
      error.status === 401 &&
      error.message === "Expired Firebase session",
  );

  assert.equal(unauthorizedErrors.length, 1);
  assert.equal(unauthorizedErrors[0]?.status, 401);
  assert.equal(unauthorizedErrors[0]?.code, "UNAUTHORIZED");
});

test("api client can return response metadata for flows that need status-sensitive handling", async (t) => {
  const originalFetch = globalThis.fetch;

  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (): Promise<Response> =>
    new Response(JSON.stringify({ task_id: "task-123" }), {
      status: 202,
      headers: { "Content-Type": "application/json", "X-Test": "ok" },
    });

  const client = createApiClient({
    baseUrl: "http://localhost:8000/api/v1",
    getAccessToken: async () => "firebase-token",
  });

  const response = await client.requestWithMeta?.<{ task_id: string }>("/jobs/job-123/screenshots/extract", {
    auth: "required",
    body: { timestamp_ms: 12500 },
    method: "POST",
  });

  assert.deepEqual(response?.data, { task_id: "task-123" });
  assert.equal(response?.status, 202);
  assert.equal(response?.headers.get("X-Test"), "ok");
});

test("api client requires NEXT_PUBLIC_API_BASE_URL before issuing requests", async () => {
  const client = createApiClient({
    baseUrl: "",
  });

  await assert.rejects(
    client.get("/projects"),
    (error: unknown) =>
      error instanceof Error &&
      error.message === "Public runtime config is missing NEXT_PUBLIC_API_BASE_URL.",
  );
});
