import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  InstructionWorkspaceQuickNav,
  instructionWorkspaceQuickLinks,
} from "../../src/features/instructions/components/instruction-workspace-quick-nav";

test("workspace quick nav exposes anchor links for each instruction work area", () => {
  const html = renderToStaticMarkup(<InstructionWorkspaceQuickNav />);

  assert.match(html, /aria-label="Instruction workspace quick links"/);
  assert.match(html, /Quick jump/);

  for (const link of instructionWorkspaceQuickLinks) {
    assert.match(html, new RegExp(`href="${link.href}"`));
    assert.match(html, new RegExp(`>${link.label}</a>`));
  }
});
