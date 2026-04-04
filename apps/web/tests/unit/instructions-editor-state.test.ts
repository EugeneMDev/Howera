import assert from "node:assert/strict";
import test from "node:test";

import type { Instruction } from "../../src/features/instructions/api";
import {
  adoptLatestInstructionBase,
  applyInstructionSaveSuccess,
  applyInstructionVersionConflict,
  applyLoadedInstructionSnapshot,
  createInstructionEditorState,
  isInstructionEditorDirty,
  reloadInstructionEditorFromLatest,
  updateInstructionDraft,
} from "../../src/features/instructions/editor-state";

function createInstruction(overrides: Partial<Instruction> = {}): Instruction {
  return {
    instruction_id: "inst-123",
    job_id: "job-123",
    markdown: "# Version 1",
    updated_at: "2026-03-25T08:00:00Z",
    validation_status: "PASS",
    version: 1,
    ...overrides,
  };
}

test("instruction editor hydrates draft state from loaded instruction", () => {
  const state = applyLoadedInstructionSnapshot(createInstructionEditorState(), createInstruction());

  assert.equal(state.draftMarkdown, "# Version 1");
  assert.equal(state.instruction?.version, 1);
  assert.equal(isInstructionEditorDirty(state), false);
});

test("instruction editor save success updates version metadata in place", () => {
  const loaded = applyLoadedInstructionSnapshot(createInstructionEditorState(), createInstruction());
  const dirty = updateInstructionDraft(loaded, "# Edited");
  const saved = applyInstructionSaveSuccess(
    dirty,
    createInstruction({
      markdown: "# Edited",
      updated_at: "2026-03-25T09:00:00Z",
      validated_at: "2026-03-25T09:00:01Z",
      validation_errors: [
        {
          code: "MISSING_CHECKLIST",
          message: "Add the missing checklist block.",
          path: "markdown.blocks[2]",
        },
      ],
      validation_status: "FAIL",
      version: 2,
    }),
  );

  assert.equal(saved.draftMarkdown, "# Edited");
  assert.equal(saved.instruction?.version, 2);
  assert.equal(saved.instruction?.validation_status, "FAIL");
  assert.equal(saved.instruction?.validated_at, "2026-03-25T09:00:01Z");
  assert.equal(saved.instruction?.validation_errors?.[0]?.code, "MISSING_CHECKLIST");
  assert.equal(saved.feedback?.title, "Save complete");
  assert.equal(isInstructionEditorDirty(saved), false);
});

test("instruction editor refresh applies latest validation snapshot after regenerate when clean", () => {
  const loaded = applyLoadedInstructionSnapshot(createInstructionEditorState(), createInstruction());
  const refreshed = applyLoadedInstructionSnapshot(
    loaded,
    createInstruction({
      markdown: "# Regenerated version",
      validated_at: "2026-03-25T10:00:00Z",
      validation_errors: [
        {
          code: "MISSING_SUMMARY",
          message: "Add a summary section.",
        },
      ],
      validation_status: "FAIL",
      version: 3,
    }),
  );

  assert.equal(refreshed.instruction?.version, 3);
  assert.equal(refreshed.instruction?.validation_status, "FAIL");
  assert.equal(refreshed.instruction?.validation_errors?.[0]?.code, "MISSING_SUMMARY");
  assert.equal(refreshed.latestInstruction?.validated_at, "2026-03-25T10:00:00Z");
  assert.equal(refreshed.draftMarkdown, "# Regenerated version");
  assert.equal(isInstructionEditorDirty(refreshed), false);
});

test("instruction editor conflict preserves unsaved local draft", () => {
  const loaded = applyLoadedInstructionSnapshot(createInstructionEditorState(), createInstruction());
  const dirty = updateInstructionDraft(loaded, "# Local unsaved change");
  const conflicted = applyInstructionVersionConflict(
    dirty,
    { base_version: 1, current_version: 2 },
    createInstruction({
      markdown: "# Server version 2",
      updated_at: "2026-03-25T09:00:00Z",
      version: 2,
    }),
  );

  assert.equal(conflicted.draftMarkdown, "# Local unsaved change");
  assert.equal(conflicted.instruction?.version, 1);
  assert.equal(conflicted.latestInstruction?.version, 2);
  assert.deepEqual(conflicted.conflict, { base_version: 1, current_version: 2 });
  assert.equal(isInstructionEditorDirty(conflicted), true);
});

test("instruction editor can reload latest version explicitly after conflict", () => {
  const loaded = applyLoadedInstructionSnapshot(createInstructionEditorState(), createInstruction());
  const conflicted = applyInstructionVersionConflict(
    updateInstructionDraft(loaded, "# Local unsaved change"),
    { base_version: 1, current_version: 2 },
    createInstruction({
      markdown: "# Server version 2",
      updated_at: "2026-03-25T09:00:00Z",
      version: 2,
    }),
  );
  const reloaded = reloadInstructionEditorFromLatest(conflicted);

  assert.equal(reloaded.draftMarkdown, "# Server version 2");
  assert.equal(reloaded.instruction?.version, 2);
  assert.equal(reloaded.conflict, null);
  assert.equal(isInstructionEditorDirty(reloaded), false);
});

test("instruction editor can keep draft and adopt latest version as new base", () => {
  const loaded = applyLoadedInstructionSnapshot(createInstructionEditorState(), createInstruction());
  const conflicted = applyInstructionVersionConflict(
    updateInstructionDraft(loaded, "# Local merge draft"),
    { base_version: 1, current_version: 2 },
    createInstruction({
      markdown: "# Server version 2",
      updated_at: "2026-03-25T09:00:00Z",
      version: 2,
    }),
  );
  const adopted = adoptLatestInstructionBase(conflicted);

  assert.equal(adopted.draftMarkdown, "# Local merge draft");
  assert.equal(adopted.instruction?.version, 2);
  assert.equal(adopted.conflict, null);
  assert.equal(adopted.feedback?.title, "Draft kept for manual merge");
  assert.equal(isInstructionEditorDirty(adopted), true);
});
