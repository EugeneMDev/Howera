# Story 9.1: Request Screenshot Extraction and Poll Task

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to request screenshot extraction at a target timestamp,
so that I can attach visuals to instruction context.

## Acceptance Criteria

1. Given the editor submits a contract-valid extraction request, when the backend accepts it, then the UI shows task acknowledgement and pending state immediately and the extraction task is pollable to completion.
2. Given the extraction task reaches terminal state, when results are available, then the UI surfaces anchor or asset linkage returned by the task and preserves surrounding editor context.

## Tasks / Subtasks

- [x] Add screenshot extraction form or action flow from the instruction workspace.
- [x] Submit extraction requests with contract-valid timestamp and context fields.
- [x] Poll screenshot task status with bounded refresh and freshness indicators.
- [x] Surface resulting anchor and asset linkage without resetting editor context.
- [x] Handle duplicate or replayed extraction requests safely in the UI.
- [x] Add tests for extraction request, polling, completion, replay, and failure states.

## Dev Notes

### Developer Context Section

- Backend extraction and screenshot-task polling already exist in Story 5.1.
- This story is the frontend entrypoint for the screenshot and anchor lifecycle.
- Keep extraction UX contextual to the editor rather than forcing modal-heavy workflow jumps.

### Technical Requirements

- Use `POST /jobs/{jobId}/screenshots/extract` and `GET /screenshot-tasks/{taskId}`.
- Preserve active editor state and selection while extraction runs.
- Show pending, succeeded, and failed task states explicitly.
- Do not create duplicate client-side state for replayed tasks.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/screenshots/`
- `apps/web/src/features/tasks/`
- `apps/web/src/features/instructions/`
- `apps/web/tests/`

### Testing Requirements

- Verify extraction request acknowledgement and task polling.
- Verify terminal task state surfaces returned anchor or asset linkage.
- Verify replayed requests do not create ambiguous duplicate UI state.
- Verify surrounding editor state is preserved through extraction flow.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/5-1-extract-screenshot-with-alignment-parameters-and-anchor-metadata.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/5-1-extract-screenshot-with-alignment-parameters-and-anchor-metadata.md`

### Completion Notes List

- 2026-03-24: Created Story 9.1 artifact with screenshot extraction submit/poll UX scope.
- 2026-03-24: Captured task lifecycle, replay-safe UI, and editor-context-preservation requirements.
- 2026-03-25: Implemented an instruction-workspace screenshot extraction panel with timestamp, context, strategy, format, and idempotency inputs.
- 2026-03-25: Added bounded screenshot-task polling, replay-safe task restoration, and explicit anchor/asset linkage rendering without disturbing local editor state.
- 2026-03-25: Added unit coverage for screenshot request shaping, replay/success/failure copy, panel rendering, and shared client response-metadata handling.
- 2026-03-25: Verified with `npm run check` in `apps/web`, `make check` in `apps/api`, and a direct `/openapi.json` path/code assertion for screenshot extract and polling routes.

### File List

- `_bmad-output/implementation-artifacts/9-1-request-screenshot-extraction-and-poll-task.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/instructions/components/instruction-editor-screen.tsx`
- `apps/web/src/features/screenshots/api.ts`
- `apps/web/src/features/screenshots/extraction.ts`
- `apps/web/src/features/screenshots/hooks.ts`
- `apps/web/src/features/screenshots/components/instruction-screenshot-panel.tsx`
- `apps/web/src/shared/api/client.ts`
- `apps/web/tests/unit/api-client.test.ts`
- `apps/web/tests/unit/instruction-screenshot-panel.test.tsx`
- `apps/web/tests/unit/screenshots-api.test.ts`
- `apps/web/tests/unit/screenshots-extraction.test.ts`

### Change Log

- 2026-03-24: Created Story 9.1 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-25: Completed Story 9.1 with screenshot extraction request/poll UI, replay-safe task tracking, task linkage surfacing, and AC-mapped web verification.
