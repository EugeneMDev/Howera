# Story 8.4: Surface Validation Status and Validation Errors

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want validation status visible while editing,
so that I can maintain publish-ready instruction quality.

## Acceptance Criteria

1. Given instruction payload contains validation metadata, when the instruction is loaded or refreshed, then the UI displays `validation_status`, validation errors, and validation timing and validation UI updates after save or regenerate.
2. Given validation errors exist, when the editor reviews them, then the UI presents actionable messages without blocking ongoing editing and does not invent data absent from the contract.

## Tasks / Subtasks

- [x] Render validation status summary from instruction payload metadata.
- [x] Show validation errors, warnings, and timestamps in the editor workspace.
- [x] Refresh validation UI after successful save or regenerate without full page reload.
- [x] Keep validation messaging actionable and contract-bound rather than heuristic.
- [x] Ensure validation feedback does not block editing unless the backend contract says so.
- [x] Add tests for validation status rendering and live updates after instruction changes.

## Dev Notes

### Developer Context Section

- Backend validation metadata is already established in Story 4.4.
- This story is display-focused and should not introduce new client-side validation rules that diverge from backend results.
- Validation must stay visible during long editing sessions without disrupting the editor.

### Technical Requirements

- Reuse validation fields returned by instruction read and write flows.
- Keep UI messaging aligned to `validation_status` and `validation_errors` from the contract.
- Update validation state after save and regenerate responses.
- Do not invent validation results absent from backend payloads.
- Current implementation uses a dedicated validation panel in the instruction workspace, surfaces `validation_status`, `validation_errors`, `validated_at`, and `validator_version` when present, and relies on existing save success plus instruction refresh paths to update the displayed server-authored validation snapshot.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/instructions/`
- `apps/web/src/shared/ui/`
- `apps/web/tests/`

### Testing Requirements

- Verify validation status, errors, and timestamps render from payload data.
- Verify validation state refreshes after save and regenerate.
- Verify editing remains possible while validation errors are displayed.
- Verify no client-side fabricated validation output appears.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `apps/api/app/schemas/instruction.py`
- `_bmad-output/implementation-artifacts/4-4-structural-validation-on-create-and-update-with-persisted-result.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `apps/api/app/schemas/instruction.py`
- `_bmad-output/implementation-artifacts/4-4-structural-validation-on-create-and-update-with-persisted-result.md`

### Completion Notes List

- 2026-03-24: Created Story 8.4 artifact with validation-surface scope for the instruction workspace.
- 2026-03-24: Captured contract-bound validation display requirements and non-blocking editor behavior.
- 2026-03-25: Added a dedicated validation panel to the instruction workspace with contract-bound status, timestamp, validator version, and structured issue rendering while keeping editing non-blocking.
- 2026-03-25: Added unit coverage for validation panel rendering plus editor-state validation refresh behavior after save and regenerate snapshots, then passed `make lint`, `make test`, `make typecheck`, `make build`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/8-4-surface-validation-status-and-validation-errors.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/instructions/components/instruction-editor-screen.tsx`
- `apps/web/src/features/instructions/components/instruction-validation-panel.tsx`
- `apps/web/tests/unit/instruction-validation-panel.test.tsx`
- `apps/web/tests/unit/instructions-editor-state.test.ts`

### Change Log

- 2026-03-24: Created Story 8.4 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-25: Implemented contract-bound validation summary and issue rendering in the instruction workspace and verified refresh behavior after save and regenerate-driven reloads.
- 2026-03-25: Added validation-focused unit tests, passed `make check`, and moved Story 8.4 to `done`.
