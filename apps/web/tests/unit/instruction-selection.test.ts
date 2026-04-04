import assert from "node:assert/strict";
import test from "node:test";

import { captureTextSelection, restoreTextSelection } from "../../src/features/instructions/selection";

test("text selection helpers capture and restore textarea ranges", () => {
  const target: {
    selectionDirection: "backward" | "forward" | "none";
    selectionEnd: number;
    selectionStart: number;
    setSelectionRange: (
      start: number,
      end: number,
      direction?: "backward" | "forward" | "none",
    ) => void;
  } = {
    selectionDirection: "forward" as const,
    selectionEnd: 14,
    selectionStart: 4,
    setSelectionRange(start: number, end: number, direction?: "backward" | "forward" | "none") {
      this.selectionStart = start;
      this.selectionEnd = end;
      this.selectionDirection = direction ?? "none";
    },
  };

  const snapshot = captureTextSelection(target);

  target.selectionStart = 0;
  target.selectionEnd = 0;
  target.selectionDirection = "none";

  const restored = restoreTextSelection(target, snapshot);

  assert.equal(restored, true);
  assert.deepEqual(snapshot, { direction: "forward", end: 14, start: 4 });
  assert.equal(target.selectionStart, 4);
  assert.equal(target.selectionEnd, 14);
  assert.equal(target.selectionDirection, "forward");
});

test("text selection restore is a no-op without target or snapshot", () => {
  assert.equal(restoreTextSelection(null, null), false);
});
