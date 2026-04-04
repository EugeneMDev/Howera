# Story 8.3: Request Targeted Regenerate and Poll Task Status

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to regenerate a selected block or range,
so that I can improve content without rerunning the full workflow.

## Acceptance Criteria

1. Given the editor selects a valid `block_id` or `char_range`, when they submit regenerate with a `client_request_id`, then the UI shows task acknowledgement immediately and polling begins automatically.
2. Given the regenerate task reaches `SUCCEEDED` or `FAILED`, when polling receives terminal state, then the UI surfaces the result or sanitized failure details and keeps the editor in a recoverable state.

## Tasks / Subtasks

- [x] Add selection-aware regenerate entrypoints for `block_id` and `char_range`.
- [x] Submit regenerate requests with `base_version` and `client_request_id`.
- [x] Implement regenerate task polling with bounded retries and freshness indicators.
- [x] Surface task success and sanitized failure outcomes inline without losing draft context.
- [x] Support replay-safe UX when the backend returns an existing task for a duplicate request.
- [x] Add tests for request creation, replay, polling, success, and sanitized failure handling.

## Dev Notes

### Developer Context Section

- Backend regenerate request and polling behavior exist in Stories 4.5 and 4.6.
- This story must preserve optimistic-concurrency context from Story 8.1.
- UX requires regenerate to feel targeted, explicit, and recoverable.

### Technical Requirements

- Use `POST /instructions/{instructionId}/regenerate` and `GET /tasks/{taskId}`.
- Send contract-valid selection payloads only (`block_id` xor `char_range`).
- Preserve `client_request_id` for replay-safe UX and diagnostics.
- Show sanitized failure output only; do not expose prompt or transcript internals.
- Current implementation adds a dedicated regenerate panel beside the editor, builds only contract-valid `block_id` or `char_range` payloads from editor state, and reuses bounded polling to track regenerate tasks until terminal state or bounded exhaustion.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/instructions/`
- `apps/web/src/features/tasks/`
- `apps/web/src/shared/hooks/`
- `apps/web/tests/`

### Testing Requirements

- Verify valid regenerate request enters a visible pending state and starts polling.
- Verify duplicate request handling surfaces replay rather than duplicate task creation.
- Verify success and failure terminal states preserve local editor recoverability.
- Verify polling is bounded and shows refresh state clearly.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/implementation-artifacts/4-5-request-targeted-regeneration-with-idempotency-and-provenance.md`
- `_bmad-output/implementation-artifacts/4-6-poll-regenerate-task-status-with-sanitized-outcomes.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/implementation-artifacts/4-5-request-targeted-regeneration-with-idempotency-and-provenance.md`
- `_bmad-output/implementation-artifacts/4-6-poll-regenerate-task-status-with-sanitized-outcomes.md`

### Completion Notes List

- 2026-03-24: Created Story 8.3 artifact with targeted-regenerate request and polling scope.
- 2026-03-24: Captured selection validation, replay-safe UX, and sanitized terminal-state requirements.
- 2026-03-25: Added regenerate request/task contract helpers, selection builders, replay-aware task descriptions, and a bounded polling hook wrapper for targeted instruction regenerate flows.
- 2026-03-25: Extended the instruction editor with a regenerate side panel for `char_range` and `block_id` submissions, inline task status feedback, replay-safe request IDs, and refresh controls that preserve local draft recoverability.
- 2026-03-25: Added unit coverage for regenerate helpers and API calls, then passed `make lint`, `make test`, `make typecheck`, `make build`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/8-3-request-targeted-regenerate-and-poll-task-status.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/instructions/api.ts`
- `apps/web/src/features/instructions/hooks.ts`
- `apps/web/src/features/instructions/regenerate.ts`
- `apps/web/src/features/instructions/regenerate-hooks.ts`
- `apps/web/src/features/instructions/components/instruction-editor-screen.tsx`
- `apps/web/src/features/instructions/components/instruction-regenerate-panel.tsx`
- `apps/web/tests/unit/instructions-api.test.ts`
- `apps/web/tests/unit/instructions-regenerate.test.ts`

### Change Log

- 2026-03-24: Created Story 8.3 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-25: Implemented targeted regenerate request creation, replay-safe task polling, and inline regenerate status UX in `apps/web`.
- 2026-03-25: Added regenerate-focused unit tests, passed `make check`, and moved Story 8.3 to `done`.
