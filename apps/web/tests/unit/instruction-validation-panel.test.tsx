import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { InstructionValidationPanel } from "../../src/features/instructions/components/instruction-validation-panel";
import type { Instruction } from "../../src/features/instructions/api";
import { formatDateTime } from "../../src/shared/lib/format-date";

function createInstruction(overrides: Partial<Instruction> = {}): Instruction {
  return {
    instruction_id: "inst-123",
    job_id: "job-123",
    markdown: "# Demo",
    updated_at: "2026-03-25T08:00:00Z",
    validated_at: "2026-03-25T09:15:00Z",
    validation_errors: [],
    validation_status: "PASS",
    validator_version: "validator-v1",
    version: 2,
    ...overrides,
  };
}

test("validation panel renders pass summary and timestamp from contract payload", () => {
  const html = renderToStaticMarkup(
    <InstructionValidationPanel
      instruction={createInstruction()}
      latestServerVersion={2}
    />,
  );

  assert.match(html, /Server-authored quality signal/);
  assert.match(html, /PASS/);
  assert.match(
    html,
    new RegExp(`Last validated ${formatDateTime("2026-03-25T09:15:00Z").replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`),
  );
  assert.match(html, /Validator version: validator-v1\./);
  assert.match(
    html,
    /No validation errors are attached to the currently loaded instruction version\./,
  );
});

test("validation panel renders structured failing issues without blocking edit copy", () => {
  const html = renderToStaticMarkup(
    <InstructionValidationPanel
      instruction={createInstruction({
        validated_at: null,
        validation_errors: [
          {
            code: "MISSING_HEADING",
            message: "Add a top-level heading before publishing.",
            path: "markdown.blocks[0]",
          },
        ],
        validation_status: "FAIL",
        validator_version: null,
        version: 3,
      })}
      latestServerVersion={4}
    />,
  );

  assert.match(html, /FAIL/);
  assert.match(html, /Latest known v4/);
  assert.match(html, /Validation timestamp is not available yet\./);
  assert.match(html, /Editing remains available while these contract-provided issues are visible\./);
  assert.match(html, /MISSING_HEADING/);
  assert.match(html, /Add a top-level heading before publishing\./);
  assert.match(html, /markdown\.blocks\[0\]/);
});
