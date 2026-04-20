import assert from "node:assert/strict";
import test from "node:test";

import { ApiClientError } from "../../src/shared/api/errors";
import {
  describeAnnotatedScreenshot,
  describeAssetLifecycleError,
  describeAttachedUpload,
  describeSoftDeletedAsset,
  normalizeScreenshotUploadMimeType,
} from "../../src/features/screenshots/asset-lifecycle";

test("screenshot asset lifecycle helpers normalize upload types and success feedback", () => {
  assert.equal(normalizeScreenshotUploadMimeType("image/png"), "image/png");
  assert.equal(normalizeScreenshotUploadMimeType("image/jpeg"), "image/jpeg");
  assert.equal(normalizeScreenshotUploadMimeType("image/webp"), "image/webp");
  assert.equal(normalizeScreenshotUploadMimeType("image/svg+xml"), null);

  assert.deepEqual(
    describeSoftDeletedAsset({
      active_asset_id: "asset-2",
      anchor_id: "anchor-1",
      deleted_asset_id: "asset-3",
    }),
    {
      description:
        "Asset asset-3 was deleted. Anchor anchor-1 now resolves to active asset asset-2.",
      title: "Asset deleted",
      tone: "success",
    },
  );

  assert.deepEqual(
    describeAttachedUpload({
      active_asset_id: "asset-9",
      addressing: {
        address_type: "block_id",
        block_id: "intro",
      },
      created_at: "2026-03-25T10:00:00Z",
      id: "anchor-1",
      instruction_id: "inst-1",
      instruction_version_id: "3",
      updated_at: "2026-03-25T10:05:00Z",
    }),
    {
      description:
        "Uploaded asset is now attached to anchor anchor-1. Active asset asset-9 is linked to source version 3.",
      title: "Uploaded asset attached",
      tone: "success",
    },
  );

  assert.deepEqual(
    describeAnnotatedScreenshot(
      {
        active_asset_id: "asset-annotated-2",
        anchor_id: "anchor-1",
        base_asset_id: "asset-9",
        ops_hash: "ops-123",
        rendered_asset_id: "asset-annotated-2",
      },
      "asset-9",
    ),
    {
      description:
        "Annotation rendering completed. Anchor anchor-1 now resolves from base asset asset-9 to rendered asset asset-annotated-2.",
      title: "Annotated asset rendered",
      tone: "success",
    },
  );

  assert.deepEqual(
    describeAnnotatedScreenshot(
      {
        active_asset_id: "asset-annotated-2",
        anchor_id: "anchor-1",
        base_asset_id: "asset-9",
        ops_hash: "ops-123",
        rendered_asset_id: "asset-annotated-2",
      },
      "asset-annotated-2",
    ),
    {
      description:
        "Matching normalized annotation operations already resolve to rendered asset asset-annotated-2. The current active view stays unchanged.",
      title: "Existing annotated asset reused",
      tone: "success",
    },
  );
});

test("screenshot asset lifecycle errors preserve no-leak and validation-safe messaging", () => {
  assert.deepEqual(
    describeAssetLifecycleError(
      new ApiClientError(404, {
        code: "RESOURCE_NOT_FOUND",
        message: "Resource not found",
      }),
      "upload",
    ),
    {
      description:
        "The screenshot asset context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
      title: "Screenshot asset context unavailable",
      tone: "danger",
    },
  );

  assert.deepEqual(
    describeAssetLifecycleError(
      new ApiClientError(400, {
        code: "VALIDATION_ERROR",
        message: "Duplicate idempotency_key payload differs from first accepted request.",
      }),
      "replace",
    ),
    {
      description: "Duplicate idempotency_key payload differs from first accepted request.",
      title: "Replacement request rejected",
      tone: "warning",
    },
  );
});
