# Story 10.2: Download Completed Exports Securely

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want download action only when an export is ready,
so that artifact access remains secure and predictable.

## Acceptance Criteria

1. Given export status is not `SUCCEEDED`, when the editor views or attempts download, then download action is disabled or guarded and readiness guidance is displayed.
2. Given export status is `SUCCEEDED`, when the editor requests download, then the frontend uses the signed URL immediately and does not persist the URL in unsafe browser storage.

## Tasks / Subtasks

- [x] Gate download actions on export `SUCCEEDED` state only.
- [x] Show readiness guidance and disabled states for pending or failed exports.
- [x] Trigger download using signed URLs without persisting them in local storage or telemetry.
- [x] Reflect expiry or missing-download conditions safely to the user.
- [x] Add tests for disabled download behavior and successful secure download flow.

## Dev Notes

### Developer Context Section

- Backend download URL policy and strict scoping exist in Story 6.5.
- Frontend must treat signed URLs as ephemeral secrets.
- This story depends on export status visibility from Story 10.1.

### Technical Requirements

- Use `GET /exports/{exportId}` as the source of `download_url` availability.
- Never persist signed URLs outside ephemeral in-memory action flow.
- Keep download affordances disabled or guarded until export is `SUCCEEDED`.
- Present clear readiness and expiry messaging when download is unavailable.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/exports/`
- `apps/web/src/shared/lib/`
- `apps/web/tests/`

### Testing Requirements

- Verify non-succeeded exports cannot trigger download.
- Verify succeeded exports use the provided signed URL immediately.
- Verify download URLs are not persisted in local storage or telemetry.
- Verify readiness guidance remains clear for non-ready exports.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/implementation-artifacts/6-5-issue-strictly-scoped-signed-download-url.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/implementation-artifacts/6-5-issue-strictly-scoped-signed-download-url.md`

### Completion Notes List

- 2026-03-24: Created Story 10.2 artifact with secure-download scope for completed exports.
- 2026-03-24: Captured signed-URL ephemerality and readiness-gating requirements for frontend implementation.
- 2026-04-03: Bound each export download control to its readiness guidance text and kept download gating on `SUCCEEDED` records only.
- 2026-04-03: Added unit coverage for disabled download rendering and the immediate signed-URL helper path without `localStorage` or `sessionStorage` access.
- 2026-04-03: Verified `make lint`, `make test`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/10-2-download-completed-exports-securely.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/exports/components/instruction-export-panel.tsx`
- `apps/web/tests/unit/instruction-export-panel.test.tsx`
- `apps/web/tests/unit/download.test.ts`

### Change Log

- 2026-03-24: Created Story 10.2 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-04-03: Completed Story 10.2 secure-download guidance/test coverage and moved frontend story status to `done`.
