# Story 9.2: Inspect Anchor Context and Version Visibility

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to inspect anchor addressing and active asset context,
so that screenshot references remain understandable across instruction versions.

## Acceptance Criteria

1. Given an instruction has anchors, when the editor opens anchor details, then block addressing, active asset state, and instruction version context are shown and no-leak not-found behavior is preserved.
2. Given instruction version context changes, when anchor mapping is still valid, then the UI preserves anchor references and warns only when user action is required.

## Tasks / Subtasks

- [x] Add anchor list and anchor detail views inside the instruction workspace.
- [x] Query anchor collections and single-anchor details through the shared API client.
- [x] Show block addressing, active asset metadata, deletion state, and instruction-version context.
- [x] Preserve stable anchor references when the viewed instruction version changes and mapping remains valid.
- [x] Add warning states only when anchor context requires user intervention.
- [x] Add tests for anchor visibility, no-leak `404`, and version-context preservation behavior.

## Dev Notes

### Developer Context Section

- Backend anchor addressability and cross-version traceability are already implemented by Story 5.6.
- This story is inspection-focused and should establish UI patterns reused by asset lifecycle and annotation flows.
- Keep anchor context tied to instruction versions and backend responses rather than client heuristics.

### Technical Requirements

- Use `GET /instructions/{instructionId}/anchors` and `GET /anchors/{anchorId}`.
- Respect `instruction_version_id` and visibility context returned by the contract.
- Preserve generic `404` behavior for missing or unauthorized anchors.
- Surface warnings only when the returned data says the user must act.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/screenshots/`
- `apps/web/src/features/instructions/`
- `apps/web/src/shared/api/`
- `apps/web/tests/`

### Testing Requirements

- Verify anchor list and detail rendering.
- Verify no-leak behavior for missing or unauthorized anchor routes.
- Verify version switching preserves stable anchors where supported.
- Verify warning states appear only when backend data requires them.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/implementation-artifacts/5-6-anchor-addressing-persistence-policy-and-cross-version-traceability.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/implementation-artifacts/5-6-anchor-addressing-persistence-policy-and-cross-version-traceability.md`

### Completion Notes List

- 2026-03-24: Created Story 9.2 artifact with anchor-inspector and version-visibility scope.
- 2026-03-24: Captured cross-version preservation and no-leak requirements for frontend implementation.
- 2026-03-25: Implemented an instruction-workspace anchor inspector with anchor list selection, active-asset context, deleted-asset visibility, and backend-driven version-resolution rendering.
- 2026-03-25: Added shared anchor list/detail API bindings plus a selection-preserving anchor hook that keeps the selected anchor stable while the viewed instruction version changes.
- 2026-03-25: Added tests for anchor API paths, resolution/warning helpers, rendered detail state, and generic no-leak error handling.
- 2026-03-25: Verified with `npm run check` in `apps/web`, `make check` in `apps/api`, and a direct `/openapi.json` path/code assertion for anchor list/detail routes.

### File List

- `_bmad-output/implementation-artifacts/9-2-inspect-anchor-context-and-version-visibility.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/instructions/components/instruction-editor-screen.tsx`
- `apps/web/src/features/screenshots/api.ts`
- `apps/web/src/features/screenshots/anchors.ts`
- `apps/web/src/features/screenshots/anchor-hooks.ts`
- `apps/web/src/features/screenshots/components/instruction-anchor-panel.tsx`
- `apps/web/tests/unit/instruction-anchor-panel.test.tsx`
- `apps/web/tests/unit/screenshots-anchors.test.ts`
- `apps/web/tests/unit/screenshots-api.test.ts`

### Change Log

- 2026-03-24: Created Story 9.2 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-25: Completed Story 9.2 with anchor inspection, version-visibility projection, backend-gated warning states, and AC-mapped web verification.
