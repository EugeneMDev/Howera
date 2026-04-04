import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { InstructionTranscriptPanel } from "../../src/features/instructions/components/instruction-transcript-panel";
import type { useInstructionTranscript } from "../../src/features/instructions/transcript-hooks";

function createTranscriptState(
  overrides: Partial<ReturnType<typeof useInstructionTranscript>> = {},
): ReturnType<typeof useInstructionTranscript> {
  return {
    currentStatus: null,
    error: null,
    hasMore: false,
    isLoadingMore: false,
    isRefreshing: false,
    items: [],
    loadMore: async () => {},
    nextCursor: null,
    refresh() {},
    settledRevision: 0,
    status: "success",
    ...overrides,
  } as ReturnType<typeof useInstructionTranscript>;
}

test("closed transcript panel exposes an explicit expand relationship", () => {
  const html = renderToStaticMarkup(
    <InstructionTranscriptPanel
      onToggle={() => {}}
      transcript={createTranscriptState()}
      transcriptOpen={false}
    />,
  );

  assert.match(html, /Open transcript/);
  assert.match(html, /aria-controls="instruction-transcript-section"/);
  assert.match(html, /aria-expanded="false"/);
});

test("open transcript panel exposes collapse state and transcript content", () => {
  const html = renderToStaticMarkup(
    <InstructionTranscriptPanel
      onToggle={() => {}}
      transcript={createTranscriptState({
        items: [{ end_ms: 3200, start_ms: 1200, text: "Transcript line" }],
      })}
      transcriptOpen={true}
    />,
  );

  assert.match(html, /Hide transcript/);
  assert.match(html, /aria-controls="instruction-transcript-section"/);
  assert.match(html, /aria-expanded="true"/);
  assert.match(html, /Transcript line/);
});
