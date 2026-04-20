import assert from "node:assert/strict";
import test from "node:test";

import { ApiClientError } from "../../src/shared/api/errors";
import {
  appendTranscriptSegments,
  applyTranscriptNotReady,
  applyTranscriptPage,
  createTranscriptPanelState,
  formatTranscriptTimestamp,
} from "../../src/features/instructions/transcript-state";

test("transcript pagination appends without reordering segments", () => {
  const initialState = createTranscriptPanelState(2);
  const firstPage = applyTranscriptPage(
    initialState,
    {
      items: [
        { start_ms: 0, end_ms: 1200, text: "First" },
        { start_ms: 1500, end_ms: 2200, text: "Second" },
      ],
      limit: 2,
      next_cursor: "2",
    },
    "replace",
  );
  const secondPage = applyTranscriptPage(
    firstPage,
    {
      items: [
        { start_ms: 2400, end_ms: 3000, text: "Third" },
        { start_ms: 3100, end_ms: 4200, text: "Fourth" },
      ],
      limit: 2,
      next_cursor: null,
    },
    "append",
  );

  assert.deepEqual(secondPage.items.map((item) => item.text), ["First", "Second", "Third", "Fourth"]);
  assert.equal(secondPage.nextCursor, null);
});

test("transcript segment append deduplicates repeated page items", () => {
  const items = appendTranscriptSegments(
    [{ start_ms: 0, end_ms: 1200, text: "First" }],
    [
      { start_ms: 0, end_ms: 1200, text: "First" },
      { start_ms: 1300, end_ms: 1800, text: "Second" },
    ],
  );

  assert.deepEqual(items.map((item) => item.text), ["First", "Second"]);
});

test("transcript not-ready state preserves contract current_status detail", () => {
  const state = applyTranscriptNotReady(
    createTranscriptPanelState(120),
    new ApiClientError(409, {
      code: "TRANSCRIPT_NOT_READY",
      details: { current_status: "AUDIO_EXTRACTING" },
      message: "Transcript is not available for this job state.",
    }),
  );

  assert.equal(state.status, "not-ready");
  assert.equal(state.currentStatus, "AUDIO_EXTRACTING");
  assert.equal(state.error, "Transcript is not available for this job state.");
});

test("transcript timestamps format deterministically", () => {
  assert.equal(formatTranscriptTimestamp(1234), "0:01.234");
  assert.equal(formatTranscriptTimestamp(61_005), "1:01.005");
  assert.equal(formatTranscriptTimestamp(3_661_009), "1:01:01.009");
});
