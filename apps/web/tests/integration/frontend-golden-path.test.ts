import assert from "node:assert/strict";
import test from "node:test";

import { requestExport, getExport } from "../../src/features/exports/api";
import { getInstruction, updateInstruction } from "../../src/features/instructions/api";
import { createJob, confirmJobUpload, getJobTranscript, runJob } from "../../src/features/jobs/api";
import { createProject } from "../../src/features/projects/api";
import {
  getScreenshotTask,
  listScreenshotAnchors,
  requestScreenshotExtraction,
} from "../../src/features/screenshots/api";
import { createApiClient } from "../../src/shared/api/client";

interface MockExchange {
  assertBody?: (body: unknown) => void;
  label: string;
  method: "GET" | "POST" | "PUT";
  path: string;
  response: unknown;
  status: number;
}

interface MockRequestRecord {
  authHeader: string | null;
  body: unknown;
  method: string;
  path: string;
}

interface GoldenPathResult {
  instructionVersion: number;
  mdExportStatus: string;
  pdfExportStatus: string;
  projectId: string;
  requestCount: number;
  screenshotAnchorId: string;
}

function createJsonResponse(status: number, payload: unknown): Response {
  const body = payload === null ? "" : JSON.stringify(payload);

  return new Response(body, {
    headers: body ? { "Content-Type": "application/json" } : undefined,
    status,
  });
}

function normalizeRequestBody(body: BodyInit | null | undefined): unknown {
  if (body === undefined || body === null) {
    return null;
  }

  if (typeof body === "string") {
    return body.length > 0 ? (JSON.parse(body) as unknown) : null;
  }

  if (body instanceof URLSearchParams) {
    return Object.fromEntries(body.entries());
  }

  return body;
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}

function createSequencedFetchMock(exchanges: MockExchange[]) {
  const requests: MockRequestRecord[] = [];
  let currentExchangeIndex = 0;

  const fetchImpl: typeof fetch = async (input, init = {}) => {
    if (typeof input !== "string") {
      throw new Error("Golden path mock only supports string request URLs.");
    }

    const url = new URL(input);
    const method = (init.method ?? "GET").toUpperCase();
    const path = `${url.pathname}${url.search}`;
    const exchange = exchanges[currentExchangeIndex];

    if (!exchange) {
      throw new Error(`Unexpected extra request ${method} ${path}`);
    }

    if (exchange.method !== method || exchange.path !== path) {
      throw new Error(
        `Mock step "${exchange.label}" expected ${exchange.method} ${exchange.path}, received ${method} ${path}`,
      );
    }

    const headers = new Headers(init.headers);
    const authHeader = headers.get("authorization");
    if (authHeader !== "Bearer test:ci-editor:editor") {
      throw new Error(`Mock auth header missing for step "${exchange.label}"`);
    }

    const body = normalizeRequestBody(init.body);
    exchange.assertBody?.(body);

    requests.push({
      authHeader,
      body,
      method,
      path,
    });
    currentExchangeIndex += 1;

    return createJsonResponse(exchange.status, exchange.response);
  };

  return {
    assertComplete() {
      assert.equal(
        currentExchangeIndex,
        exchanges.length,
        `Expected ${exchanges.length} mocked requests, received ${currentExchangeIndex}.`,
      );
    },
    fetchImpl,
    requests,
  };
}

async function withMockFetch<T>(fetchImpl: typeof fetch, fn: () => Promise<T>): Promise<T> {
  const originalFetch = globalThis.fetch;
  (globalThis as typeof globalThis & { fetch: typeof fetch }).fetch = fetchImpl;

  try {
    return await fn();
  } finally {
    (globalThis as typeof globalThis & { fetch: typeof fetch }).fetch = originalFetch;
  }
}

async function runGoldenPathStep<T>(label: string, fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    throw new Error(`Frontend golden path failed at step "${label}": ${formatError(error)}`);
  }
}

async function runMockFrontendGoldenPath(fetchImpl: typeof fetch): Promise<GoldenPathResult> {
  return withMockFetch(fetchImpl, async () => {
    const apiClient = createApiClient({
      baseUrl: "https://mock.api.local/api/v1",
      getAccessToken: async () => "test:ci-editor:editor",
    });

    const project = await runGoldenPathStep("create project", () =>
      createProject(apiClient, { name: "Demo Project" }),
    );
    const job = await runGoldenPathStep("create job", () => createJob(apiClient, project.id));

    await runGoldenPathStep("confirm upload", () =>
      confirmJobUpload(apiClient, job.id, { video_uri: "gs://bucket/demo-video.mp4" }),
    );

    await runGoldenPathStep("run workflow", () => runJob(apiClient, job.id));
    await runGoldenPathStep("load transcript", () =>
      getJobTranscript(apiClient, job.id, { limit: 3 }),
    );

    const loadedInstruction = await runGoldenPathStep("load draft instruction", () =>
      getInstruction(apiClient, "inst-123"),
    );

    const updatedInstruction = await runGoldenPathStep("save instruction edits", () =>
      updateInstruction(apiClient, loadedInstruction.instruction_id, {
        base_version: loadedInstruction.version,
        markdown: "# Demo Project\n\n[block:intro]\nPolished draft",
      }),
    );

    const screenshotTask = await runGoldenPathStep("request screenshot extraction", () =>
      requestScreenshotExtraction(apiClient, job.id, {
        block_id: "intro",
        format: "png",
        idempotency_key: "screenshot-123",
        instruction_id: loadedInstruction.instruction_id,
        instruction_version_id: String(updatedInstruction.version),
        offset_ms: 0,
        strategy: "precise",
        timestamp_ms: 12_500,
      }),
    );

    const completedScreenshotTask = await runGoldenPathStep("poll screenshot task", () =>
      getScreenshotTask(apiClient, screenshotTask.task_id),
    );

    const anchors = await runGoldenPathStep("load screenshot anchors", () =>
      listScreenshotAnchors(apiClient, loadedInstruction.instruction_id, {
        instruction_version_id: String(updatedInstruction.version),
      }),
    );

    const mdExport = await runGoldenPathStep("request MD export", () =>
      requestExport(apiClient, job.id, {
        format: "MD_ZIP",
        idempotency_key: "export-md-123",
        instruction_version_id: String(updatedInstruction.version),
      }),
    );

    const mdExportResult = await runGoldenPathStep("poll MD export", () =>
      getExport(apiClient, mdExport.id),
    );

    const pdfExport = await runGoldenPathStep("request PDF export", () =>
      requestExport(apiClient, job.id, {
        format: "PDF",
        idempotency_key: "export-pdf-123",
        instruction_version_id: String(updatedInstruction.version),
      }),
    );

    const pdfExportResult = await runGoldenPathStep("poll PDF export", () =>
      getExport(apiClient, pdfExport.id),
    );

    return {
      instructionVersion: updatedInstruction.version,
      mdExportStatus: mdExportResult.status,
      pdfExportStatus: pdfExportResult.status,
      projectId: project.id,
      requestCount: 14,
      screenshotAnchorId:
        completedScreenshotTask.anchor_id ?? anchors[0]?.id ?? "missing-screenshot-anchor",
    };
  });
}

test("mock-mode golden path covers create, run, edit, screenshot, and export flows", async () => {
  const fetchMock = createSequencedFetchMock([
    {
      assertBody(body) {
        assert.deepEqual(body, { name: "Demo Project" });
      },
      label: "create project",
      method: "POST",
      path: "/api/v1/projects",
      response: {
        created_at: "2026-04-04T08:00:00Z",
        id: "project-123",
        name: "Demo Project",
      },
      status: 201,
    },
    {
      assertBody(body) {
        assert.equal(body, null);
      },
      label: "create job",
      method: "POST",
      path: "/api/v1/projects/project-123/jobs",
      response: {
        created_at: "2026-04-04T08:01:00Z",
        id: "job-123",
        project_id: "project-123",
        status: "CREATED",
      },
      status: 201,
    },
    {
      assertBody(body) {
        assert.deepEqual(body, { video_uri: "gs://bucket/demo-video.mp4" });
      },
      label: "confirm upload",
      method: "POST",
      path: "/api/v1/jobs/job-123/confirm-upload",
      response: {
        job: {
          created_at: "2026-04-04T08:01:00Z",
          id: "job-123",
          manifest: {
            video_uri: "gs://bucket/demo-video.mp4",
          },
          project_id: "project-123",
          status: "UPLOADED",
        },
        replayed: false,
      },
      status: 200,
    },
    {
      assertBody(body) {
        assert.equal(body, null);
      },
      label: "run workflow",
      method: "POST",
      path: "/api/v1/jobs/job-123/run",
      response: {
        dispatch_id: "dispatch-123",
        job_id: "job-123",
        replayed: false,
        status: "AUDIO_EXTRACTING",
      },
      status: 202,
    },
    {
      label: "load transcript",
      method: "GET",
      path: "/api/v1/jobs/job-123/transcript?limit=3",
      response: {
        items: [
          { end_ms: 1200, start_ms: 0, text: "Welcome to the demo." },
          { end_ms: 2500, start_ms: 1400, text: "We are generating a stable draft." },
          { end_ms: 4100, start_ms: 2800, text: "Screenshot extraction will follow." },
        ],
        limit: 3,
        next_cursor: null,
      },
      status: 200,
    },
    {
      label: "load draft instruction",
      method: "GET",
      path: "/api/v1/instructions/inst-123",
      response: {
        instruction_id: "inst-123",
        job_id: "job-123",
        markdown: "# Demo Project\n\n[block:intro]\nInitial draft",
        updated_at: "2026-04-04T08:05:00Z",
        validated_at: "2026-04-04T08:05:30Z",
        validation_errors: [],
        validation_status: "PASS",
        validator_version: "validator-v1",
        version: 2,
      },
      status: 200,
    },
    {
      assertBody(body) {
        assert.deepEqual(body, {
          base_version: 2,
          markdown: "# Demo Project\n\n[block:intro]\nPolished draft",
        });
      },
      label: "save instruction edits",
      method: "PUT",
      path: "/api/v1/instructions/inst-123",
      response: {
        instruction_id: "inst-123",
        job_id: "job-123",
        markdown: "# Demo Project\n\n[block:intro]\nPolished draft",
        updated_at: "2026-04-04T08:06:00Z",
        validated_at: "2026-04-04T08:06:30Z",
        validation_errors: [],
        validation_status: "PASS",
        validator_version: "validator-v1",
        version: 3,
      },
      status: 200,
    },
    {
      assertBody(body) {
        assert.deepEqual(body, {
          block_id: "intro",
          format: "png",
          idempotency_key: "screenshot-123",
          instruction_id: "inst-123",
          instruction_version_id: "3",
          offset_ms: 0,
          strategy: "precise",
          timestamp_ms: 12500,
        });
      },
      label: "request screenshot extraction",
      method: "POST",
      path: "/api/v1/jobs/job-123/screenshots/extract",
      response: {
        operation: "extract",
        status: "PENDING",
        task_id: "screenshot-task-123",
      },
      status: 202,
    },
    {
      label: "poll screenshot task",
      method: "GET",
      path: "/api/v1/screenshot-tasks/screenshot-task-123",
      response: {
        anchor_id: "anchor-123",
        asset_id: "asset-123",
        operation: "extract",
        status: "SUCCEEDED",
        task_id: "screenshot-task-123",
      },
      status: 200,
    },
    {
      label: "load screenshot anchors",
      method: "GET",
      path: "/api/v1/instructions/inst-123/anchors?instruction_version_id=3",
      response: [
        {
          active_asset_id: "asset-123",
          addressing: {
            address_type: "block_id",
            block_id: "intro",
          },
          assets: [],
          created_at: "2026-04-04T08:07:00Z",
          id: "anchor-123",
          instruction_id: "inst-123",
          instruction_version_id: "3",
          updated_at: "2026-04-04T08:07:10Z",
        },
      ],
      status: 200,
    },
    {
      assertBody(body) {
        assert.deepEqual(body, {
          format: "MD_ZIP",
          idempotency_key: "export-md-123",
          instruction_version_id: "3",
        });
      },
      label: "request MD export",
      method: "POST",
      path: "/api/v1/jobs/job-123/exports",
      response: {
        created_at: "2026-04-04T08:08:00Z",
        format: "MD_ZIP",
        id: "export-md-123",
        identity_key: "identity-md-123",
        instruction_version_id: "3",
        job_id: "job-123",
        screenshot_set_hash: "hash-md-123",
        status: "REQUESTED",
        updated_at: "2026-04-04T08:08:00Z",
      },
      status: 202,
    },
    {
      label: "poll MD export",
      method: "GET",
      path: "/api/v1/exports/export-md-123",
      response: {
        created_at: "2026-04-04T08:08:00Z",
        download_url: "https://downloads.howera.local/export-md-123.zip?sig=abc",
        download_url_expires_at: "2026-04-04T08:23:00Z",
        format: "MD_ZIP",
        id: "export-md-123",
        identity_key: "identity-md-123",
        instruction_version_id: "3",
        job_id: "job-123",
        screenshot_set_hash: "hash-md-123",
        status: "SUCCEEDED",
        updated_at: "2026-04-04T08:09:00Z",
      },
      status: 200,
    },
    {
      assertBody(body) {
        assert.deepEqual(body, {
          format: "PDF",
          idempotency_key: "export-pdf-123",
          instruction_version_id: "3",
        });
      },
      label: "request PDF export",
      method: "POST",
      path: "/api/v1/jobs/job-123/exports",
      response: {
        created_at: "2026-04-04T08:09:30Z",
        format: "PDF",
        id: "export-pdf-123",
        identity_key: "identity-pdf-123",
        instruction_version_id: "3",
        job_id: "job-123",
        screenshot_set_hash: "hash-pdf-123",
        status: "REQUESTED",
        updated_at: "2026-04-04T08:09:30Z",
      },
      status: 202,
    },
    {
      label: "poll PDF export",
      method: "GET",
      path: "/api/v1/exports/export-pdf-123",
      response: {
        created_at: "2026-04-04T08:09:30Z",
        download_url: "https://downloads.howera.local/export-pdf-123.pdf?sig=def",
        download_url_expires_at: "2026-04-04T08:24:30Z",
        format: "PDF",
        id: "export-pdf-123",
        identity_key: "identity-pdf-123",
        instruction_version_id: "3",
        job_id: "job-123",
        screenshot_set_hash: "hash-pdf-123",
        status: "SUCCEEDED",
        updated_at: "2026-04-04T08:10:30Z",
      },
      status: 200,
    },
  ]);

  const result = await runMockFrontendGoldenPath(fetchMock.fetchImpl);

  fetchMock.assertComplete();
  assert.deepEqual(result, {
    instructionVersion: 3,
    mdExportStatus: "SUCCEEDED",
    pdfExportStatus: "SUCCEEDED",
    projectId: "project-123",
    requestCount: 14,
    screenshotAnchorId: "anchor-123",
  });
  assert.equal(fetchMock.requests.length, 14);
  assert.equal(
    fetchMock.requests.every((request) => request.authHeader === "Bearer test:ci-editor:editor"),
    true,
  );
});

test("golden path failures identify the broken frontend step clearly", async () => {
  const fetchMock = createSequencedFetchMock([
    {
      assertBody(body) {
        assert.deepEqual(body, { name: "Demo Project" });
      },
      label: "create project",
      method: "POST",
      path: "/api/v1/projects",
      response: {
        created_at: "2026-04-04T08:00:00Z",
        id: "project-123",
        name: "Demo Project",
      },
      status: 201,
    },
    {
      assertBody(body) {
        assert.equal(body, null);
      },
      label: "create job",
      method: "POST",
      path: "/api/v1/projects/project-123/jobs",
      response: {
        created_at: "2026-04-04T08:01:00Z",
        id: "job-123",
        project_id: "project-123",
        status: "CREATED",
      },
      status: 201,
    },
    {
      assertBody(body) {
        assert.deepEqual(body, { video_uri: "gs://bucket/demo-video.mp4" });
      },
      label: "confirm upload",
      method: "POST",
      path: "/api/v1/jobs/job-123/confirm-upload",
      response: {
        job: {
          created_at: "2026-04-04T08:01:00Z",
          id: "job-123",
          project_id: "project-123",
          status: "UPLOADED",
        },
        replayed: false,
      },
      status: 200,
    },
    {
      assertBody(body) {
        assert.equal(body, null);
      },
      label: "run workflow",
      method: "POST",
      path: "/api/v1/jobs/job-123/run",
      response: {
        code: "UPSTREAM_ERROR",
        message: "Workflow dispatch failed.",
      },
      status: 502,
    },
  ]);

  await assert.rejects(
    () => runMockFrontendGoldenPath(fetchMock.fetchImpl),
    /Frontend golden path failed at step "run workflow": Workflow dispatch failed\./,
  );
});
