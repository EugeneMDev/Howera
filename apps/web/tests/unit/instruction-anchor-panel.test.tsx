import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { InstructionAnchorPanel } from "../../src/features/screenshots/components/instruction-anchor-panel";

test("anchor panel renders lifecycle controls, unresolved warning, and asset fallback feedback", () => {
  const html = renderToStaticMarkup(
    <InstructionAnchorPanel
      anchorsState={{
        anchors: [
          {
            active_asset_id: "asset-2",
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
                is_deleted: true,
                kind: "EXTRACTED",
                mime_type: "image/png",
                version: 1,
                width: 1280,
              },
              {
                anchor_id: "anchor-1",
                created_at: "2026-03-25T10:05:00Z",
                height: 720,
                id: "asset-2",
                image_uri: "s3://bucket/asset-2.png",
                is_deleted: false,
                kind: "ANNOTATED",
                mime_type: "image/png",
                version: 2,
                width: 1280,
              },
            ],
            created_at: "2026-03-25T10:00:00Z",
            id: "anchor-1",
            instruction_id: "inst-123",
            instruction_version_id: "1",
            updated_at: "2026-03-25T10:06:00Z",
          },
        ],
        detailFeedback: null,
        detailStatus: "success",
        hasAnchors: true,
        listFeedback: null,
        listStatus: "success",
        refresh() {},
        selectedAnchor: {
          active_asset_id: "asset-2",
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
              is_deleted: true,
              kind: "EXTRACTED",
              mime_type: "image/png",
              version: 1,
              width: 1280,
            },
            {
              anchor_id: "anchor-1",
              created_at: "2026-03-25T10:05:00Z",
              height: 720,
              id: "asset-2",
              image_uri: "s3://bucket/asset-2.png",
              is_deleted: false,
              kind: "ANNOTATED",
              mime_type: "image/png",
              version: 2,
              width: 1280,
            },
          ],
          created_at: "2026-03-25T10:00:00Z",
          id: "anchor-1",
          instruction_id: "inst-123",
          instruction_version_id: "1",
          resolution: {
            resolution_state: "unresolved",
            source_instruction_version_id: "1",
            target_instruction_version_id: "3",
            trace: {
              method: "block_index_remap",
              reason: "unable_to_map_block_id",
            },
          },
          updated_at: "2026-03-25T10:06:00Z",
        },
        selectedAnchorId: "anchor-1",
        selectedAnchorSummary: {
          active_asset_id: "asset-2",
          addressing: {
            address_type: "block_id",
            block_id: "intro",
          },
          assets: [],
          created_at: "2026-03-25T10:00:00Z",
          id: "anchor-1",
          instruction_id: "inst-123",
          instruction_version_id: "1",
          updated_at: "2026-03-25T10:06:00Z",
        },
        setSelectedAnchorId() {},
        visibilityContextDescription: "Current view projects anchors into instruction version 3.",
        visibilityTargetVersionId: "3",
      }}
      currentInstructionVersion={3}
      jobId="job-123"
      latestServerVersion={4}
      lifecycle={{
        annotationFeedback: {
          description:
            "Matching normalized annotation operations already resolve to rendered asset asset-1. The current active view stays unchanged.",
          title: "Existing annotated asset reused",
          tone: "success",
        },
        annotationIsSubmitting: false,
        annotationLastIdempotencyKey: "annotate-123",
        annotationResult: {
          active_asset_id: "asset-1",
          anchor_id: "anchor-1",
          base_asset_id: "asset-2",
          ops_hash: "ops-123",
          rendered_asset_id: "asset-1",
        },
        assetPreview: {
          active_asset_id: "asset-1",
          anchor_id: "anchor-1",
          deleted_asset_id: "asset-2",
        },
        async deleteAsset() {},
        deleteFeedback: {
          description: "Asset asset-2 was deleted. Anchor anchor-1 now resolves to active asset asset-1.",
          title: "Asset deleted",
          tone: "success",
        },
        dismissAnnotationFeedback() {},
        dismissDeleteFeedback() {},
        dismissReplaceFeedback() {},
        dismissUploadFeedback() {},
        pendingDeleteAssetId: null,
        async refreshReplaceTask() {},
        replaceFeedback: {
          description:
            "Screenshot replacement completed and linked anchor anchor-1 to asset asset-1.",
          title: "Screenshot replaced",
          tone: "success",
        },
        replaceIsSubmitting: false,
        replaceLastIdempotencyKey: "replace-123",
        replacePolling: {
          active: false,
          attemptsRemaining: 0,
          intervalMs: 2500,
          lastPolledAt: "2026-03-25T10:08:00Z",
          maxAttempts: 10,
          reason: "screenshot-replace-task-status",
          startedAt: "2026-03-25T10:07:00Z",
          watchValue: "replace-task-123",
        },
        replaceTask: {
          anchor_id: "anchor-1",
          asset_id: "asset-1",
          operation: "replace",
          replayed: true,
          status: "SUCCEEDED",
          task_id: "replace-task-123",
        },
        stopReplacePolling() {},
        async submitAnnotation() {
          return true;
        },
        async submitReplace() {},
        async submitUploadAndAttach() {
          return true;
        },
        uploadFeedback: {
          description:
            "Uploaded asset is now attached to anchor anchor-1. Active asset asset-9 is linked to source version 3.",
          title: "Uploaded asset attached",
          tone: "success",
        },
        uploadIsSubmitting: false,
        uploadLastIdempotencyKey: "attach-123",
      }}
    />,
  );

  assert.match(html, /Inspect and manage deterministic screenshot assets/);
  assert.match(html, /Current view projects anchors into instruction version 3/);
  assert.match(html, /Anchor requires attention/);
  assert.match(html, /Annotate active asset/);
  assert.match(html, /Last annotation outcome/);
  assert.match(html, /ops-123/);
  assert.match(html, /Last annotation idempotency key: annotate-123/);
  assert.match(html, /Replace active asset/);
  assert.match(html, /Upload and attach custom asset/);
  assert.match(html, /Task replace-task-123/);
  assert.match(html, /Asset asset-2 was deleted\. Anchor anchor-1 now resolves to active asset asset-1\./);
  assert.match(html, /Last attach idempotency key: attach-123/);
  assert.match(html, /Delete asset/);
});

test("anchor panel preserves the last annotation outcome when a later render fails", () => {
  const html = renderToStaticMarkup(
    <InstructionAnchorPanel
      anchorsState={{
        anchors: [
          {
            active_asset_id: "asset-annotated-1",
            addressing: {
              address_type: "block_id",
              block_id: "intro",
            },
            assets: [
              {
                anchor_id: "anchor-1",
                created_at: "2026-03-25T10:00:00Z",
                height: 720,
                id: "asset-base-1",
                image_uri: "s3://bucket/asset-base-1.png",
                is_deleted: false,
                kind: "EXTRACTED",
                mime_type: "image/png",
                version: 1,
                width: 1280,
              },
              {
                anchor_id: "anchor-1",
                created_at: "2026-03-25T10:04:00Z",
                height: 720,
                id: "asset-annotated-1",
                image_uri: "s3://bucket/asset-annotated-1.png",
                is_deleted: false,
                kind: "ANNOTATED",
                mime_type: "image/png",
                version: 2,
                width: 1280,
              },
            ],
            created_at: "2026-03-25T10:00:00Z",
            id: "anchor-1",
            instruction_id: "inst-123",
            instruction_version_id: "1",
            updated_at: "2026-03-25T10:06:00Z",
          },
        ],
        detailFeedback: null,
        detailStatus: "success",
        hasAnchors: true,
        listFeedback: null,
        listStatus: "success",
        refresh() {},
        selectedAnchor: {
          active_asset_id: "asset-annotated-1",
          addressing: {
            address_type: "block_id",
            block_id: "intro",
          },
          assets: [
            {
              anchor_id: "anchor-1",
              created_at: "2026-03-25T10:00:00Z",
              height: 720,
              id: "asset-base-1",
              image_uri: "s3://bucket/asset-base-1.png",
              is_deleted: false,
              kind: "EXTRACTED",
              mime_type: "image/png",
              version: 1,
              width: 1280,
            },
            {
              anchor_id: "anchor-1",
              created_at: "2026-03-25T10:04:00Z",
              height: 720,
              id: "asset-annotated-1",
              image_uri: "s3://bucket/asset-annotated-1.png",
              is_deleted: false,
              kind: "ANNOTATED",
              mime_type: "image/png",
              version: 2,
              width: 1280,
            },
          ],
          created_at: "2026-03-25T10:00:00Z",
          id: "anchor-1",
          instruction_id: "inst-123",
          instruction_version_id: "1",
          resolution: {
            resolution_state: "retain",
            source_instruction_version_id: "1",
            target_instruction_version_id: "1",
          },
          updated_at: "2026-03-25T10:06:00Z",
        },
        selectedAnchorId: "anchor-1",
        selectedAnchorSummary: {
          active_asset_id: "asset-annotated-1",
          addressing: {
            address_type: "block_id",
            block_id: "intro",
          },
          assets: [],
          created_at: "2026-03-25T10:00:00Z",
          id: "anchor-1",
          instruction_id: "inst-123",
          instruction_version_id: "1",
          updated_at: "2026-03-25T10:06:00Z",
        },
        setSelectedAnchorId() {},
        visibilityContextDescription: "Current view targets source version 1.",
        visibilityTargetVersionId: "1",
      }}
      currentInstructionVersion={1}
      jobId="job-123"
      latestServerVersion={1}
      lifecycle={{
        annotationFeedback: {
          description: "Renderer unavailable",
          title: "Annotation request rejected",
          tone: "danger",
        },
        annotationIsSubmitting: false,
        annotationLastIdempotencyKey: "annotate-456",
        annotationResult: {
          active_asset_id: "asset-annotated-1",
          anchor_id: "anchor-1",
          base_asset_id: "asset-base-1",
          ops_hash: "ops-prev",
          rendered_asset_id: "asset-annotated-1",
        },
        assetPreview: null,
        async deleteAsset() {},
        deleteFeedback: null,
        dismissAnnotationFeedback() {},
        dismissDeleteFeedback() {},
        dismissReplaceFeedback() {},
        dismissUploadFeedback() {},
        pendingDeleteAssetId: null,
        async refreshReplaceTask() {},
        replaceFeedback: null,
        replaceIsSubmitting: false,
        replaceLastIdempotencyKey: null,
        replacePolling: {
          active: false,
          attemptsRemaining: 10,
          intervalMs: 2500,
          lastPolledAt: null,
          maxAttempts: 10,
          reason: "screenshot-replace-task-status",
          startedAt: null,
          watchValue: null,
        },
        replaceTask: null,
        stopReplacePolling() {},
        async submitAnnotation() {
          return false;
        },
        async submitReplace() {},
        async submitUploadAndAttach() {
          return false;
        },
        uploadFeedback: null,
        uploadIsSubmitting: false,
        uploadLastIdempotencyKey: null,
      }}
    />,
  );

  assert.match(html, /Annotation request rejected/);
  assert.match(html, /Renderer unavailable/);
  assert.match(html, /Last annotation outcome/);
  assert.match(html, /ops-prev/);
});
