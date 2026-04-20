# Story 9.3: Manage Screenshot Asset Lifecycle

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to upload, attach, replace, and delete screenshot assets on anchors,
so that visuals stay accurate while preserving deterministic asset state.

## Acceptance Criteria

1. Given the editor uploads or replaces an asset through the current contract flows, when the operation succeeds, then the UI reflects the new active asset deterministically and duplicate action submission does not create ambiguous state.
2. Given the editor deletes an asset or an operation fails, when the response returns, then the UI reflects fallback or preserved active state correctly and surfaces validation or auth errors safely.

## Tasks / Subtasks

- [x] Implement upload-ticket, upload-confirm, and attach-upload flows for custom screenshot assets.
- [x] Implement replace and delete asset actions for anchors with clear active-asset updates.
- [x] Keep asset-lifecycle mutations replay-safe and prevent duplicate in-flight submissions.
- [x] Reflect fallback or preserved active asset state after delete and failure responses.
- [x] Add error handling for validation, auth, and no-leak failure cases.
- [x] Add tests for upload, attach, replace, delete, replay, and fallback UI behavior.

## Dev Notes

### Developer Context Section

- Backend lifecycle flows already exist in Stories 5.2, 5.3, and 5.4.
- Frontend must present these as deterministic asset-state transitions rather than ad hoc file actions.
- Signed URL usage must remain ephemeral and never persist sensitive upload artifacts unsafely.

### Technical Requirements

- Use `POST /anchors/{anchorId}/replace`, `DELETE /anchors/{anchorId}/assets/{assetId}`, `POST /jobs/{jobId}/screenshots/uploads`, `POST /jobs/{jobId}/screenshots/uploads/{uploadId}/confirm`, and `POST /anchors/{anchorId}/attach-upload`.
- Reflect active-asset version changes only from backend responses.
- Prevent duplicate mutation clicks while operations are in flight.
- Keep signed URL handling in memory only.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/screenshots/`
- `apps/web/src/shared/api/`
- `apps/web/src/shared/hooks/`
- `apps/web/tests/`

### Testing Requirements

- Verify upload, confirm, and attach flows succeed and update active asset state.
- Verify replace and delete flows preserve deterministic UI state.
- Verify replay or duplicate clicks do not create ambiguous asset state.
- Verify failure cases surface safe error messaging and fallback behavior.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/implementation-artifacts/5-2-replace-existing-screenshot-asset-for-anchor-with-versioning.md`
- `_bmad-output/implementation-artifacts/5-3-soft-delete-screenshot-asset-and-resolve-active-fallback.md`
- `_bmad-output/implementation-artifacts/5-4-upload-custom-image-via-signed-url-and-confirm-attach.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/implementation-artifacts/5-2-replace-existing-screenshot-asset-for-anchor-with-versioning.md`
- `_bmad-output/implementation-artifacts/5-3-soft-delete-screenshot-asset-and-resolve-active-fallback.md`
- `_bmad-output/implementation-artifacts/5-4-upload-custom-image-via-signed-url-and-confirm-attach.md`

### Completion Notes List

- 2026-03-24: Created Story 9.3 artifact with asset upload, attach, replace, and delete scope.
- 2026-03-24: Captured deterministic active-asset, replay-safety, and signed-URL handling requirements.
- 2026-03-25: Added frontend replace polling, custom upload attach orchestration, and soft-delete actions to the anchor inspector.
- 2026-03-25: Kept signed upload URLs ephemeral, projected active-asset fallback from backend responses, and blocked duplicate mutation clicks while operations are in flight.
- 2026-03-25: Verified with `npm run check` in `apps/web`, `make lint`, `make test`, and `make check` in `apps/api`, plus direct `/openapi.json` assertions for the five lifecycle routes.

### File List

- `_bmad-output/implementation-artifacts/9-3-manage-screenshot-asset-lifecycle.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/instructions/components/instruction-editor-screen.tsx`
- `apps/web/src/features/screenshots/api.ts`
- `apps/web/src/features/screenshots/anchors.ts`
- `apps/web/src/features/screenshots/asset-hooks.ts`
- `apps/web/src/features/screenshots/asset-lifecycle.ts`
- `apps/web/src/features/screenshots/components/instruction-anchor-panel.tsx`
- `apps/web/src/features/screenshots/extraction.ts`
- `apps/web/tests/unit/instruction-anchor-panel.test.tsx`
- `apps/web/tests/unit/screenshots-api.test.ts`
- `apps/web/tests/unit/screenshots-anchors.test.ts`
- `apps/web/tests/unit/screenshots-assets.test.ts`
- `apps/web/tests/unit/screenshots-extraction.test.ts`

### Change Log

- 2026-03-24: Created Story 9.3 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-25: Implemented replace, delete, upload, confirm, and attach UI flows for screenshot assets and marked the story `done`.
