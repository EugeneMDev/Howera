import assert from "node:assert/strict";
import test from "node:test";

import { ApiClientError } from "../../src/shared/api/errors";
import {
  applyAnchorAssetPreview,
  describeAnchorQueryError,
  describeAnchorResolution,
  findActiveAnchorAsset,
  formatAnchorAddressing,
  getAnchorResolutionTone,
  reconcileSelectedAnchorId,
} from "../../src/features/screenshots/anchors";
import type { ScreenshotAnchor } from "../../src/features/screenshots/api";

function createAnchor(overrides: Partial<ScreenshotAnchor> = {}): ScreenshotAnchor {
  return {
    active_asset_id: "asset-1",
    addressing: {
      address_type: "block_id",
      block_id: "intro",
    },
    assets: [
      {
        anchor_id: "anchor-1",
        created_at: "2026-03-25T10:00:00Z",
        height: 720,
        id: "asset-1",
        image_uri: "s3://bucket/asset-1.png",
        is_deleted: false,
        kind: "EXTRACTED",
        mime_type: "image/png",
        version: 1,
        width: 1280,
      },
    ],
    created_at: "2026-03-25T10:00:00Z",
    id: "anchor-1",
    instruction_id: "inst-123",
    instruction_version_id: "1",
    updated_at: "2026-03-25T10:05:00Z",
    ...overrides,
  };
}

test("anchor helpers preserve selection and surface active asset context", () => {
  const anchors = [createAnchor(), createAnchor({ id: "anchor-2", active_asset_id: null, assets: [] })];

  assert.equal(reconcileSelectedAnchorId("anchor-2", anchors), "anchor-2");
  assert.equal(reconcileSelectedAnchorId("missing", anchors), "anchor-1");
  assert.equal(reconcileSelectedAnchorId(null, anchors), "anchor-1");
  assert.equal(reconcileSelectedAnchorId(null, []), null);

  assert.equal(findActiveAnchorAsset(anchors[0])?.id, "asset-1");
  assert.equal(findActiveAnchorAsset(anchors[1]), null);
});

test("anchor helpers apply active asset previews for fallback and refresh state", () => {
  const anchor = createAnchor({
    active_asset_id: "asset-2",
    assets: [
      {
        anchor_id: "anchor-1",
        created_at: "2026-03-25T10:00:00Z",
        height: 720,
        id: "asset-1",
        image_uri: "s3://bucket/asset-1.png",
        is_deleted: false,
        kind: "EXTRACTED",
        mime_type: "image/png",
        version: 1,
        width: 1280,
      },
      {
        anchor_id: "anchor-1",
        created_at: "2026-03-25T10:03:00Z",
        height: 720,
        id: "asset-2",
        image_uri: "s3://bucket/asset-2.png",
        is_deleted: false,
        kind: "UPLOADED",
        mime_type: "image/png",
        version: 2,
        width: 1280,
      },
    ],
  });

  const previewed = applyAnchorAssetPreview(anchor, {
    active_asset_id: "asset-1",
    anchor_id: "anchor-1",
    deleted_asset_id: "asset-2",
  });

  assert.equal(previewed?.active_asset_id, "asset-1");
  assert.equal(previewed?.assets?.find((asset) => asset.id === "asset-2")?.is_deleted, true);
  assert.equal(findActiveAnchorAsset(previewed)?.id, "asset-1");
});

test("anchor helpers format addressing and gate warnings on unresolved resolution only", () => {
  assert.equal(
    formatAnchorAddressing({
      address_type: "block_id",
      block_id: "intro",
    }),
    "Block ID: intro",
  );
  assert.equal(
    formatAnchorAddressing({
      address_type: "char_range",
      char_range: { end_offset: 24, start_offset: 10 },
    }),
    "Char range: 10-24",
  );

  assert.equal(getAnchorResolutionTone("retain"), "success");
  assert.equal(getAnchorResolutionTone("remap"), "info");
  assert.equal(getAnchorResolutionTone("unresolved"), "warning");

  assert.deepEqual(
    describeAnchorResolution({
      resolution_state: "remap",
      source_instruction_version_id: "1",
      target_instruction_version_id: "2",
      trace: { method: "block_index_remap" },
    }),
    {
      description:
        "Anchor visibility was remapped from source version 1 into target version 2. Review the trace details, but no intervention is currently required.",
      title: "Anchor remapped for current view",
      tone: "info",
    },
  );

  assert.deepEqual(
    describeAnchorResolution({
      resolution_state: "unresolved",
      source_instruction_version_id: "1",
      target_instruction_version_id: "3",
      trace: { method: "block_index_remap" },
    }),
    {
      description:
        "Anchor visibility could not be resolved from source version 1 into target version 3. User action is required before relying on this reference.",
      title: "Anchor requires attention",
      tone: "warning",
    },
  );
});

test("anchor query errors preserve generic no-leak behavior", () => {
  assert.deepEqual(
    describeAnchorQueryError(
      new ApiClientError(404, {
        code: "RESOURCE_NOT_FOUND",
        message: "Resource not found",
      }),
    ),
    {
      description:
        "The requested anchor context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
      title: "Anchor context unavailable",
      tone: "danger",
    },
  );
});
