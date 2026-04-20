import assert from "node:assert/strict";
import test from "node:test";

import type { ApiClient, ApiRequestOptions, ApiResponse } from "../../src/shared/api/client";
import {
  annotateScreenshot,
  attachUploadedAsset,
  confirmCustomUpload,
  createCustomUploadTicket,
  getScreenshotAnchor,
  getScreenshotTask,
  listScreenshotAnchors,
  requestScreenshotExtraction,
  requestScreenshotReplacement,
  softDeleteScreenshotAsset,
  type ScreenshotAnchor,
  type ScreenshotTask,
} from "../../src/features/screenshots/api";

function createMockApiClient() {
  const calls: Array<{
    body?: ApiRequestOptions["body"];
    method: "get" | "post" | "request" | "requestWithMeta";
    options?: ApiRequestOptions;
    path: string;
  }> = [];

  const extractionTask: ScreenshotTask = {
    operation: "extract",
    status: "PENDING",
    task_id: "screenshot-task-123",
  };
  const replacementTask: ScreenshotTask = {
    anchor_id: "anchor-123",
    operation: "replace",
    status: "RUNNING",
    task_id: "replace-task-123",
  };
  const anchor: ScreenshotAnchor = {
    active_asset_id: "asset-123",
    addressing: {
      address_type: "block_id",
      block_id: "intro",
    },
    assets: [],
    created_at: "2026-03-25T10:00:00Z",
    id: "anchor-123",
    instruction_id: "inst-123",
    instruction_version_id: "2",
    updated_at: "2026-03-25T10:05:00Z",
  };

  const apiClient: ApiClient = {
    async get<T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">): Promise<T> {
      calls.push({ method: "get", options, path });
      if (path.startsWith("/instructions/") || path.startsWith("/anchors/")) {
        if (path.startsWith("/instructions/")) {
          return [anchor] as T;
        }

        return {
          ...anchor,
          resolution: {
            resolution_state: "retain",
            source_instruction_version_id: "2",
            target_instruction_version_id: "2",
          },
        } as T;
      }

      return (path.includes("replace-task") ? replacementTask : extractionTask) as T;
    },
    async post<T>(
      path: string,
      body?: ApiRequestOptions["body"],
      options?: Omit<ApiRequestOptions, "method" | "body">,
    ): Promise<T> {
      calls.push({ body, method: "post", options: options as ApiRequestOptions | undefined, path });

      if (path.endsWith("/screenshots/uploads")) {
        return {
          allowed_mime_types: ["image/png", "image/jpeg", "image/webp"],
          expires_at: "2026-03-25T10:15:00Z",
          max_size_bytes: 10485760,
          upload_id: "upload-123",
          upload_url: "https://uploads.howera.local/upload-123?sig=abc",
        } as T;
      }

      if (path.includes("/confirm")) {
        return {
          asset: {
            anchor_id: "anchor-123",
            checksum_sha256: "a".repeat(64),
            created_at: "2026-03-25T10:10:00Z",
            height: 720,
            id: "asset-uploaded-123",
            image_uri: "s3://bucket/uploaded-123.png",
            is_deleted: false,
            kind: "UPLOADED",
            mime_type: "image/png",
            upload_id: "upload-123",
            version: 4,
            width: 1280,
          },
        } as T;
      }

      if (path.endsWith("/annotations")) {
        return {
          active_asset_id: "asset-annotated-123",
          anchor_id: "anchor-123",
          base_asset_id: "asset-base-123",
          ops_hash: "ops-hash-123",
          rendered_asset_id: "asset-annotated-123",
        } as T;
      }

      return {
        ...anchor,
        active_asset_id: "asset-uploaded-123",
        instruction_version_id: "3",
      } as T;
    },
    async request<T>(path: string, options?: ApiRequestOptions): Promise<T> {
      calls.push({ method: "request", options, path });
      return {
        active_asset_id: "asset-base-123",
        anchor_id: "anchor-123",
        deleted_asset_id: "asset-123",
      } as T;
    },
    async requestWithMeta<T>(path: string, options?: ApiRequestOptions): Promise<ApiResponse<T>> {
      calls.push({ method: "requestWithMeta", options, path });
      return {
        data: (path.endsWith("/replace") ? replacementTask : extractionTask) as T,
        headers: new Headers(),
        status: 200,
      };
    },
  };

  return { apiClient, calls };
}

test("screenshot API uses contract paths for extraction and anchor inspection", async () => {
  const { apiClient, calls } = createMockApiClient();

  const task = await requestScreenshotExtraction(apiClient, "job-123", {
    char_range: {
      end_offset: 18,
      start_offset: 4,
    },
    format: "png",
    idempotency_key: "screenshot-123",
    instruction_id: "inst-123",
    instruction_version_id: "2",
    offset_ms: -250,
    strategy: "precise",
    timestamp_ms: 12500,
  });
  await getScreenshotTask(apiClient, "screenshot-task-123");
  const listedAnchors = await listScreenshotAnchors(apiClient, "inst-123", {
    include_deleted_assets: true,
    instruction_version_id: "2",
  });
  const loadedAnchor = await getScreenshotAnchor(apiClient, "anchor-123", {
    target_instruction_version_id: "2",
  });

  assert.deepEqual(calls, [
    {
      method: "requestWithMeta",
      options: {
        auth: "required",
        body: {
          anchor_id: undefined,
          block_id: undefined,
          char_range: {
            end_offset: 18,
            start_offset: 4,
          },
          format: "png",
          idempotency_key: "screenshot-123",
          instruction_id: "inst-123",
          instruction_version_id: "2",
          offset_ms: -250,
          strategy: "precise",
          timestamp_ms: 12500,
        },
        method: "POST",
      },
      path: "/jobs/job-123/screenshots/extract",
    },
    {
      method: "get",
      options: { auth: "required" },
      path: "/screenshot-tasks/screenshot-task-123",
    },
    {
      method: "get",
      options: { auth: "required" },
      path: "/instructions/inst-123/anchors?instruction_version_id=2&include_deleted_assets=true",
    },
    {
      method: "get",
      options: { auth: "required" },
      path: "/anchors/anchor-123?target_instruction_version_id=2",
    },
  ]);

  assert.deepEqual(task, {
    operation: "extract",
    replayed: true,
    status: "PENDING",
    task_id: "screenshot-task-123",
  });
  assert.equal(listedAnchors[0]?.id, "anchor-123");
  assert.equal(loadedAnchor.resolution?.resolution_state, "retain");
});

test("screenshot asset lifecycle API uses contract paths for replace, delete, upload, confirm, and attach", async () => {
  const { apiClient, calls } = createMockApiClient();

  const replaceTask = await requestScreenshotReplacement(apiClient, "anchor-123", {
    format: "webp",
    idempotency_key: "replace-123",
    instruction_version_id: "2",
    offset_ms: 75,
    strategy: "nearest_keyframe",
    timestamp_ms: 18000,
  });
  const deleted = await softDeleteScreenshotAsset(apiClient, "anchor-123", "asset-123");
  const ticket = await createCustomUploadTicket(apiClient, "job-123", {
    checksum_sha256: "a".repeat(64),
    filename: "custom.png",
    mime_type: "image/png",
    size_bytes: 2048,
  });
  const confirmed = await confirmCustomUpload(apiClient, "job-123", "upload-123", {
    checksum_sha256: "a".repeat(64),
    height: 720,
    mime_type: "image/png",
    size_bytes: 2048,
    width: 1280,
  });
  const attached = await attachUploadedAsset(apiClient, "anchor-123", {
    idempotency_key: "attach-123",
    instruction_version_id: "3",
    upload_id: "upload-123",
  });

  assert.deepEqual(calls, [
    {
      method: "requestWithMeta",
      options: {
        auth: "required",
        body: {
          format: "webp",
          idempotency_key: "replace-123",
          instruction_version_id: "2",
          offset_ms: 75,
          strategy: "nearest_keyframe",
          timestamp_ms: 18000,
        },
        method: "POST",
      },
      path: "/anchors/anchor-123/replace",
    },
    {
      method: "request",
      options: {
        auth: "required",
        method: "DELETE",
      },
      path: "/anchors/anchor-123/assets/asset-123",
    },
    {
      body: {
        checksum_sha256: "a".repeat(64),
        filename: "custom.png",
        mime_type: "image/png",
        size_bytes: 2048,
      },
      method: "post",
      options: {
        auth: "required",
      },
      path: "/jobs/job-123/screenshots/uploads",
    },
    {
      body: {
        checksum_sha256: "a".repeat(64),
        height: 720,
        mime_type: "image/png",
        size_bytes: 2048,
        width: 1280,
      },
      method: "post",
      options: {
        auth: "required",
      },
      path: "/jobs/job-123/screenshots/uploads/upload-123/confirm",
    },
    {
      body: {
        idempotency_key: "attach-123",
        instruction_version_id: "3",
        upload_id: "upload-123",
      },
      method: "post",
      options: {
        auth: "required",
      },
      path: "/anchors/anchor-123/attach-upload",
    },
  ]);

  assert.deepEqual(replaceTask, {
    anchor_id: "anchor-123",
    operation: "replace",
    replayed: true,
    status: "RUNNING",
    task_id: "replace-task-123",
  });
  assert.equal(deleted.active_asset_id, "asset-base-123");
  assert.equal(ticket.upload_id, "upload-123");
  assert.equal(confirmed.asset.upload_id, "upload-123");
  assert.equal(attached.active_asset_id, "asset-uploaded-123");
  assert.equal(attached.instruction_version_id, "3");
});

test("screenshot annotation API uses the contract annotation endpoint and payload shape", async () => {
  const { apiClient, calls } = createMockApiClient();

  const response = await annotateScreenshot(apiClient, "anchor-123", {
    base_asset_id: "asset-base-123",
    idempotency_key: "annotate-123",
    operations: [
      {
        geometry: {
          x1: 24,
          x2: 180,
          y1: 36,
          y2: 120,
        },
        op_type: "arrow",
        style: {
          color: "#ff0000",
          width: 4,
        },
      },
    ],
  });

  assert.deepEqual(calls, [
    {
      body: {
        base_asset_id: "asset-base-123",
        idempotency_key: "annotate-123",
        operations: [
          {
            geometry: {
              x1: 24,
              x2: 180,
              y1: 36,
              y2: 120,
            },
            op_type: "arrow",
            style: {
              color: "#ff0000",
              width: 4,
            },
          },
        ],
      },
      method: "post",
      options: {
        auth: "required",
      },
      path: "/anchors/anchor-123/annotations",
    },
  ]);

  assert.deepEqual(response, {
    active_asset_id: "asset-annotated-123",
    anchor_id: "anchor-123",
    base_asset_id: "asset-base-123",
    ops_hash: "ops-hash-123",
    rendered_asset_id: "asset-annotated-123",
  });
});
