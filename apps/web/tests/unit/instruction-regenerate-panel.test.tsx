import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { InstructionRegeneratePanel } from "../../src/features/instructions/components/instruction-regenerate-panel";
import type { useInstructionRegenerate } from "../../src/features/instructions/regenerate-hooks";

function createRegenerateState(
  overrides: Partial<ReturnType<typeof useInstructionRegenerate>> = {},
): ReturnType<typeof useInstructionRegenerate> {
  return {
    dismissFeedback() {},
    feedback: null,
    isSubmitting: false,
    task: null,
    ...overrides,
  } as ReturnType<typeof useInstructionRegenerate>;
}

test("regenerate panel exposes pressed state for mode selection", () => {
  const html = renderToStaticMarkup(
    <InstructionRegeneratePanel
      blockId=""
      clientRequestId="regen-123"
      isDirty={false}
      mode="char_range"
      onBlockIdChange={() => {}}
      onClientRequestIdChange={() => {}}
      onGenerateClientRequestId={() => {}}
      onModeChange={() => {}}
      onRefreshLatestInstruction={() => {}}
      onSubmitBlockId={() => {}}
      onSubmitCharRange={() => {}}
      regenerate={createRegenerateState()}
      selectedText="Selected fragment"
      selection={{ direction: "forward", end: 24, start: 4 }}
    />,
  );

  assert.match(html, /<button[^>]*aria-pressed="true"[^>]*>Char range<\/button>/);
  assert.match(html, /<button[^>]*aria-pressed="false"[^>]*>Block ID<\/button>/);
  assert.match(html, /Selected text range/);
});
