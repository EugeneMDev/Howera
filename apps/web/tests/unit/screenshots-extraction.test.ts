import assert from "node:assert/strict";
import test from "node:test";

import {
  buildScreenshotCharRange,
  createScreenshotIdempotencyKey,
  describeScreenshotPolling,
  describeScreenshotTask,
  getScreenshotTaskStatusTone,
  normalizeScreenshotBlockId,
} from "../../src/features/screenshots/extraction";

test("screenshot helpers only emit contract-valid anchor context", () => {
  assert.deepEqual(buildScreenshotCharRange(4, 12), {
    end_offset: 12,
    start_offset: 4,
  });
  assert.equal(buildScreenshotCharRange(4, 4), null);
  assert.equal(buildScreenshotCharRange(-1, 4), null);
  assert.equal(normalizeScreenshotBlockId("  block-7  "), "block-7");
  assert.equal(normalizeScreenshotBlockId("   "), null);
});

test("screenshot idempotency keys are prefixed for diagnostics", () => {
  assert.match(createScreenshotIdempotencyKey(), /^screenshot-/);
});

test("screenshot task descriptions cover replay, success, and failure states", () => {
  assert.deepEqual(
    describeScreenshotTask({
      operation: "extract",
      replayed: true,
      status: "RUNNING",
      task_id: "task-1",
    }),
    {
      description:
        "An earlier extraction request already created this screenshot task. Tracking continues from its current status without duplicating UI state.",
      title: "Existing screenshot task restored",
      tone: "info",
    },
  );

  assert.deepEqual(
    describeScreenshotTask({
      anchor_id: "anchor-123",
      asset_id: "asset-456",
      operation: "extract",
      status: "SUCCEEDED",
      task_id: "task-2",
    }),
    {
      description:
        "Screenshot extraction completed and linked anchor anchor-123 to asset asset-456.",
      title: "Screenshot extracted",
      tone: "success",
    },
  );

  assert.deepEqual(
    describeScreenshotTask({
      failure_code: "EXTRACTION_FAILED",
      failure_message: "FFmpeg execution failed.",
      operation: "extract",
      status: "FAILED",
      task_id: "task-3",
    }),
    {
      description: "FFmpeg execution failed.",
      title: "Screenshot extraction failed: EXTRACTION_FAILED",
      tone: "danger",
    },
  );

  assert.deepEqual(
    describeScreenshotTask({
      anchor_id: "anchor-123",
      asset_id: "asset-789",
      operation: "replace",
      status: "SUCCEEDED",
      task_id: "task-4",
    }),
    {
      description:
        "Screenshot replacement completed and linked anchor anchor-123 to asset asset-789.",
      title: "Screenshot replaced",
      tone: "success",
    },
  );

  assert.deepEqual(
    describeScreenshotTask({
      operation: "replace",
      replayed: true,
      status: "RUNNING",
      task_id: "task-5",
    }),
    {
      description:
        "An earlier replacement request already created this screenshot task. Tracking continues from its current status without duplicating UI state.",
      title: "Existing replacement task restored",
      tone: "info",
    },
  );
});

test("screenshot polling copy and status tones stay explicit", () => {
  assert.equal(
    describeScreenshotPolling({
      active: true,
      attemptsRemaining: 7,
      maxAttempts: 10,
    }),
    "Polling active with 7 of 10 attempts remaining.",
  );
  assert.equal(
    describeScreenshotPolling({
      active: false,
      attemptsRemaining: 0,
      maxAttempts: 10,
    }),
    "Polling stopped after 10 attempts.",
  );

  assert.equal(getScreenshotTaskStatusTone("PENDING"), "info");
  assert.equal(getScreenshotTaskStatusTone("SUCCEEDED"), "success");
  assert.equal(getScreenshotTaskStatusTone("FAILED"), "danger");
});
