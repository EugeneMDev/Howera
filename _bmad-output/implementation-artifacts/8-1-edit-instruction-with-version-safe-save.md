# Story 8.1: Edit Instruction with Version-Safe Save

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to edit instruction markdown and save safely,
so that I can refine generated content without accidental overwrite.

## Acceptance Criteria

1. Given an instruction is loaded, when the editor updates markdown and saves, then the request includes `base_version` and success updates version metadata without full page reload.
2. Given the backend returns `VERSION_CONFLICT`, when save fails, then the UI preserves unsaved local content and offers a reload or merge-oriented recovery path.

## Tasks / Subtasks

- [x] Implement instruction detail loading and editor-local draft state.
- [x] Submit instruction updates with `base_version` through the shared API client.
- [x] Reflect successful saves in-place with updated version metadata and timestamps.
- [x] Preserve dirty local content when the backend returns `VERSION_CONFLICT`.
- [x] Add reload/merge recovery affordances without clearing unsaved edits automatically.
- [x] Add tests for save success, conflict recovery, and no data loss in the editor.

## Dev Notes

### Developer Context Section

- Backend retrieval and version-safe update behavior already exist in Stories 4.2 and 4.3.
- This story is the foundation for regenerate, validation, transcript context, and anchor-aware editing.
- Keep editor UI separate from transport and optimistic-concurrency logic.

### Technical Requirements

- Use `GET /instructions/{instructionId}` and `PUT /instructions/{instructionId}`.
- Persist and submit `base_version` from the currently loaded instruction.
- Do not discard local draft content on failed saves.
- Keep success and conflict messaging explicit and contract-aligned.
- Do not invent a global instruction list endpoint in the frontend; current implementation uses an instruction hub plus a concrete `/instructions/[instructionId]` editor route because the API contract only exposes direct instruction retrieval by id.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/app/(workspace)/instructions/`
- `apps/web/src/features/instructions/`
- `apps/web/src/shared/api/`
- `apps/web/tests/`

### Testing Requirements

- Verify instruction load and version metadata rendering.
- Verify successful save updates version info without full-page reload.
- Verify `VERSION_CONFLICT` keeps the unsaved draft intact.
- Verify reload/merge recovery paths are discoverable and safe.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/implementation-artifacts/4-2-retrieve-instruction-content-by-id.md`
- `_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/implementation-artifacts/4-2-retrieve-instruction-content-by-id.md`
- `_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md`

### Completion Notes List

- 2026-03-24: Created Story 8.1 artifact with conflict-safe instruction editing scope.
- 2026-03-24: Captured `base_version` handling and draft-preservation requirements for frontend implementation.
- 2026-03-25: Added instruction API helpers, editor state utilities, conflict-safe save handling, and a dedicated `/instructions/[instructionId]` editor route in `apps/web`.
- 2026-03-25: Replaced the placeholder instructions page with a hub that opens a specific instruction by id without inventing unsupported list/search API endpoints.
- 2026-03-25: Added unit coverage for instruction API contract paths and editor conflict-recovery state transitions, then passed `make lint`, `make test`, `make typecheck`, `make build`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/8-1-edit-instruction-with-version-safe-save.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/app/(workspace)/instructions/page.tsx`
- `apps/web/src/app/(workspace)/instructions/[instructionId]/page.tsx`
- `apps/web/src/features/instructions/api.ts`
- `apps/web/src/features/instructions/editor-state.ts`
- `apps/web/src/features/instructions/hooks.ts`
- `apps/web/src/features/instructions/components/instructions-hub-screen.tsx`
- `apps/web/src/features/instructions/components/instruction-editor-screen.tsx`
- `apps/web/src/shared/ui/textarea.tsx`
- `apps/web/tests/unit/instructions-api.test.ts`
- `apps/web/tests/unit/instructions-editor-state.test.ts`

### Change Log

- 2026-03-24: Created Story 8.1 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-25: Implemented the instruction editor flow with exact-id loading, optimistic-concurrency saves, explicit `VERSION_CONFLICT` recovery, and validation metadata surfaces in `apps/web`.
- 2026-03-25: Added instruction API/state unit tests, passed `make check`, and moved Story 8.1 to `done`.
