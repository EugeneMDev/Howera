# Story 11.1: Implement Unified Error, Retry, and Polling Pattern

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want consistent error and async handling across workflows,
so that failures are understandable and recoverable.

## Acceptance Criteria

1. Given API or auth errors occur, when the UI renders failure states, then `400`, `401`, `404`, `409`, and `502` outcomes follow a shared pattern and no-leak `404` remains generic.
2. Given long-running async actions are active, when polling and retry behavior is applied, then retry is bounded and visible and destructive actions are disabled while in-flight.

## Tasks / Subtasks

- [x] Add shared error-mapping layer for common API and auth failure statuses.
- [x] Add reusable polling hook and retry pattern shared across regenerate, screenshot, export, and lifecycle actions.
- [x] Keep no-leak `404` generic and user-safe across all surfaces.
- [x] Disable destructive or conflicting actions while related mutations are in flight.
- [x] Add freshness indicators and bounded retry/polling visibility to shared async UI.
- [x] Add tests for shared error rendering and polling/retry behavior across representative flows.

## Dev Notes

### Developer Context Section

- Architecture explicitly calls for common polling hooks and unified error handling.
- This story is cross-cutting and should reduce duplicated async-state behavior before more advanced frontend flows ship.
- The shared pattern should remain contract-led and not hide backend uncertainty.

### Technical Requirements

- Normalize `400`, `401`, `404`, `409`, and `502` into reusable UI-safe error objects.
- Build shared polling hooks with bounded intervals and cancellation cleanup.
- Keep no-leak `404` generic and avoid leaking ownership details in copy.
- Disable destructive actions while conflicting mutations are active.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/tasks/`
- `apps/web/src/shared/api/`
- `apps/web/src/shared/hooks/`
- `apps/web/src/shared/ui/`
- `apps/web/tests/`

### Testing Requirements

- Verify shared error-state mapping across common HTTP failures.
- Verify polling remains bounded and exposes refresh state.
- Verify destructive actions are disabled while related work is in flight.
- Verify no-leak `404` copy remains generic.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`

### Completion Notes List

- 2026-03-24: Created Story 11.1 artifact with shared error, retry, and polling scope.
- 2026-03-24: Captured no-leak `404`, bounded retry, and in-flight action-lock requirements for frontend implementation.
- 2026-04-03: Added shared frontend feedback primitives plus a common API/auth error mapper for `400`, `401`, `404`, `409`, and `502` handling.
- 2026-04-03: Unified bounded polling timeout/copy helpers across regenerate, screenshot, export, and lifecycle flows, including explicit paused-window messaging and freshness visibility.
- 2026-04-03: Locked conflicting lifecycle controls while a mutation is in flight and added representative unit coverage for shared error/polling helpers.
- 2026-04-03: Verified `make lint`, `make test`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/11-1-implement-unified-error-retry-and-polling-pattern.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/shared/ui/feedback.ts`
- `apps/web/src/shared/api/error-feedback.ts`
- `apps/web/src/shared/hooks/use-bounded-polling.ts`
- `apps/web/src/features/exports/feedback.ts`
- `apps/web/src/features/exports/hooks.ts`
- `apps/web/src/features/instructions/regenerate.ts`
- `apps/web/src/features/instructions/regenerate-hooks.ts`
- `apps/web/src/features/screenshots/extraction.ts`
- `apps/web/src/features/screenshots/hooks.ts`
- `apps/web/src/features/screenshots/asset-lifecycle.ts`
- `apps/web/src/features/screenshots/anchors.ts`
- `apps/web/src/features/jobs/lifecycle.ts`
- `apps/web/src/features/jobs/hooks.ts`
- `apps/web/src/features/jobs/components/job-detail-screen.tsx`
- `apps/web/tests/unit/error-feedback.test.ts`
- `apps/web/tests/unit/bounded-polling.test.ts`
- `apps/web/tests/unit/exports-feedback.test.ts`
- `apps/web/tests/unit/jobs-lifecycle.test.tsx`

### Change Log

- 2026-03-24: Created Story 11.1 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-04-03: Completed Story 11.1 shared error/polling/lifecycle-lock work and moved frontend story status to `done`.
