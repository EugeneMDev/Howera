# Story 9.4: Annotate Screenshot Assets

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to apply annotation operations to screenshot assets,
so that visuals can communicate key details in the final instructions.

## Acceptance Criteria

1. Given the editor submits annotation operations, when render completes successfully, then the rendered asset becomes the active asset view and the UI preserves the operation outcome in context.
2. Given the same normalized operations are submitted again or rendering fails, when the backend responds, then replay is treated as a successful no-op and render failure leaves current UI state consistent.

## Tasks / Subtasks

- [x] Add annotation authoring UI for supported operation types.
- [x] Normalize and submit annotation operation payloads through the shared API client.
- [x] Reflect rendered-result success by switching the active asset view deterministically.
- [x] Handle replayed annotation submissions as successful no-op outcomes.
- [x] Preserve current asset state safely when rendering fails.
- [x] Add tests for annotation success, replay behavior, and failure-state consistency.

## Dev Notes

### Developer Context Section

- Backend annotation contract and deterministic rendering behavior exist in Story 5.5.
- Frontend must treat annotations as operation-log driven, not direct bitmap editing.
- This story depends on anchor and asset context already surfaced by Stories 9.2 and 9.3.

### Technical Requirements

- Use `POST /anchors/{anchorId}/annotations`.
- Preserve normalized operation ordering when constructing request payloads.
- Reflect replay/no-op responses without duplicating asset history in the UI.
- Keep render-failure handling non-destructive to the currently visible asset.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/screenshots/`
- `apps/web/src/shared/ui/`
- `apps/web/tests/`

### Testing Requirements

- Verify annotation submission switches to rendered asset on success.
- Verify replayed identical operations resolve as no-op success.
- Verify render failures leave previous asset state intact.
- Verify operation UI remains scoped to supported contract fields only.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/implementation-artifacts/5-5-annotation-operations-schema-and-deterministic-rendering.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/implementation-artifacts/5-5-annotation-operations-schema-and-deterministic-rendering.md`

### Completion Notes List

- 2026-03-24: Created Story 9.4 artifact with annotation operation-log and rendered-result scope.
- 2026-03-24: Captured replay-as-no-op and failure-consistency requirements for frontend implementation.
- 2026-03-27: Added annotation authoring UI in the screenshot anchor panel with supported operation fields, deterministic normalization preview, and current-active-asset submission flow.
- 2026-03-27: Persisted annotation outcome context in the UI so replayed identical operations surface as successful no-op reuse and later failures do not discard the last rendered result.
- 2026-03-27: Added unit coverage for annotation helpers, API contract pathing, and anchor panel success/failure rendering; verified with `make lint`, `make test`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/9-4-annotate-screenshot-assets.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/screenshots/annotations.ts`
- `apps/web/src/features/screenshots/components/instruction-anchor-panel.tsx`
- `apps/web/tests/unit/instruction-anchor-panel.test.tsx`
- `apps/web/tests/unit/screenshots-annotations.test.ts`
- `apps/web/tests/unit/screenshots-api.test.ts`
- `apps/web/tests/unit/screenshots-assets.test.ts`

### Change Log

- 2026-03-24: Created Story 9.4 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-27: Completed Story 9.4 annotation authoring, replay-safe rendered-asset switching, and failure-safe outcome preservation in the frontend.
