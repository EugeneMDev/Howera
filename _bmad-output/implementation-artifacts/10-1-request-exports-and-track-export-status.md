# Story 10.1: Request Exports and Track Export Status

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to request `MD_ZIP` and `PDF` exports and track progress,
so that I can prepare shareable deliverables confidently.

## Acceptance Criteria

1. Given the editor requests an export for the chosen instruction version, when the request is accepted or replayed, then the UI shows export record state transitions clearly and job context remains visible during async processing.
2. Given the export reaches terminal state, when status polling updates, then the UI shows `SUCCEEDED` or `FAILED` clearly and failed states expose a retry path aligned to the contract.

## Tasks / Subtasks

- [x] Add export request controls for `PDF` and `MD_ZIP` from job or instruction context.
- [x] Submit export requests with selected instruction version and handle accepted vs replay responses explicitly.
- [x] Poll export status by `export_id` with bounded refresh and visible last-updated state.
- [x] Render export state transitions and terminal summaries inside the workspace.
- [x] Expose retry or re-request affordances aligned to backend idempotency behavior.
- [x] Add tests for create-export, replay handling, polling, success, and failure UX.

## Dev Notes

### Developer Context Section

- Backend export request and status retrieval exist in Stories 6.1 and 6.4.
- This story must preserve job and instruction context while long-running export work progresses.
- Retry UX should stay aligned to backend idempotency semantics rather than inventing duplicate export flows.

### Technical Requirements

- Use `POST /jobs/{jobId}/exports` and `GET /exports/{exportId}`.
- Surface accepted (`202`) vs replay (`200`) responses clearly.
- Keep export polling bounded and user-visible.
- Render terminal states with actionable but contract-safe next steps.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/exports/`
- `apps/web/src/features/tasks/`
- `apps/web/src/app/(workspace)/jobs/`
- `apps/web/tests/`

### Testing Requirements

- Verify export creation for both supported formats.
- Verify replay handling maps to a clear existing-export state.
- Verify polling transitions through requested/running/succeeded/failed states.
- Verify failed states expose a safe retry or re-request path.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`
- `_bmad-output/implementation-artifacts/6-4-retrieve-export-status-by-export-id.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`
- `_bmad-output/implementation-artifacts/6-4-retrieve-export-status-by-export-id.md`

### Completion Notes List

- 2026-03-24: Created Story 10.1 artifact with export-request and export-status tracking scope.
- 2026-03-24: Captured accepted-vs-replay UX and bounded polling requirements for frontend implementation.
- 2026-03-27: Added a new `features/exports` slice with contract-aligned create/status API calls, replay-aware request handling, and bounded polling across all in-flight export records.
- 2026-03-27: Integrated export request and status tracking into the instruction workspace so `MD_ZIP` and `PDF` requests stay bound to the saved instruction version while job/editor context remains visible.
- 2026-03-27: Added unit coverage for export API contract pathing, replay/status feedback, and export panel rendering; verified with `make lint`, `make test`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/10-1-request-exports-and-track-export-status.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/exports/api.ts`
- `apps/web/src/features/exports/feedback.ts`
- `apps/web/src/features/exports/hooks.ts`
- `apps/web/src/features/exports/components/instruction-export-panel.tsx`
- `apps/web/src/features/instructions/components/instruction-editor-screen.tsx`
- `apps/web/tests/unit/exports-api.test.ts`
- `apps/web/tests/unit/exports-feedback.test.ts`
- `apps/web/tests/unit/instruction-export-panel.test.tsx`

### Change Log

- 2026-03-24: Created Story 10.1 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-27: Completed Story 10.1 export request controls, replay-aware status tracking, and workspace polling UX in the frontend.
