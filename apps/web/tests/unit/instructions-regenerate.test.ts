import assert from "node:assert/strict";
import test from "node:test";

import {
  buildBlockIdSelection,
  buildCharRangeSelection,
  createRegenerateClientRequestId,
  describeRegeneratePolling,
  describeRegenerateTask,
  getRegenerateTaskStatusTone,
} from "../../src/features/instructions/regenerate";

test("regenerate selection builders only emit contract-valid payloads", () => {
  assert.deepEqual(buildCharRangeSelection(4, 12), {
    char_range: {
      end_offset: 12,
      start_offset: 4,
    },
  });
  assert.equal(buildCharRangeSelection(4, 4), null);
  assert.deepEqual(buildBlockIdSelection("  step-3  "), { block_id: "step-3" });
  assert.equal(buildBlockIdSelection("   "), null);
});

test("regenerate client request ids are prefixed for diagnostics", () => {
  assert.match(createRegenerateClientRequestId(), /^regen-/);
});

test("regenerate task descriptions cover replay, success, and sanitized failure states", () => {
  assert.deepEqual(
    describeRegenerateTask({
      id: "task-1",
      requested_at: "2026-03-25T10:00:00Z",
      replayed: true,
      status: "RUNNING",
    }),
    {
      description: "Existing regenerate task restored. Polling continues from its current status.",
      title: "Existing regenerate task restored",
      tone: "info",
    },
  );

  assert.deepEqual(
    describeRegenerateTask({
      id: "task-2",
      instruction_version: 3,
      requested_at: "2026-03-25T10:00:00Z",
      status: "SUCCEEDED",
    }),
    {
      description: "Regenerate completed and produced instruction version 3.",
      title: "Regenerate completed",
      tone: "success",
    },
  );

  assert.deepEqual(
    describeRegenerateTask({
      failure_code: "REGENERATE_FAILED",
      failure_message: "Regenerate task failed.",
      id: "task-3",
      requested_at: "2026-03-25T10:00:00Z",
      status: "FAILED",
    }),
    {
      description: "Regenerate task failed.",
      title: "Regenerate failed: REGENERATE_FAILED",
      tone: "danger",
    },
  );
});

test("regenerate polling copy and status tones stay explicit", () => {
  assert.equal(
    describeRegeneratePolling({
      active: true,
      attemptsRemaining: 5,
      lastPolledAt: null,
      maxAttempts: 8,
      reason: "regenerate-task-status",
      startedAt: "2026-03-25T10:00:00Z",
    }),
    "Polling active with 5 of 8 attempts remaining.",
  );
  assert.equal(
    describeRegeneratePolling({
      active: false,
      attemptsRemaining: 0,
      lastPolledAt: "2026-03-25T10:00:00Z",
      maxAttempts: 8,
      reason: "regenerate-task-status",
      startedAt: "2026-03-25T10:00:00Z",
    }),
    "Polling stopped after 8 attempts.",
  );

  assert.equal(getRegenerateTaskStatusTone("PENDING"), "info");
  assert.equal(getRegenerateTaskStatusTone("SUCCEEDED"), "success");
  assert.equal(getRegenerateTaskStatusTone("FAILED"), "danger");
});
