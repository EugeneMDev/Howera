# Story 7.3: Create and Browse Owned Projects and Jobs

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to create and browse my projects and jobs,
so that I can manage workflow work items from the UI.

## Acceptance Criteria

1. Given an authenticated editor, when they create a project or job from the UI, then the relevant list refreshes without full page reload and contract-consistent identifiers and statuses are shown.
2. Given a project or job is missing or not owned by the editor, when the editor navigates to its route, then the UI shows a no-leak not-found state and exposes no cross-owner metadata.

## Tasks / Subtasks

- [x] Add projects list, project detail, and job list/detail routes within the workspace shell.
- [x] Implement shared project and job query modules backed by the API client.
- [x] Add create-project and create-job forms with optimistic refresh or query invalidation.
- [x] Render contract-consistent status badges and identifiers in list and detail views.
- [x] Add generic no-leak not-found states for missing or unauthorized projects and jobs.
- [x] Add UI and query tests covering create, browse, refresh, and `404` parity behavior.

## Dev Notes

### Developer Context Section

- Backend ownership and no-leak behavior are already defined in Stories 1.2 and 1.3.
- This story should establish the core workspace data-navigation patterns reused by later lifecycle and editor stories.
- Keep page components thin and push API/query logic into feature modules.
- Current implementation keeps page files thin by rendering feature-owned client screens for project list/detail, project-scoped jobs, global recent jobs, and job detail.
- Because `spec/api/openapi.yaml` does not define a global `GET /jobs` or `GET /projects/{projectId}/jobs` list endpoint, the frontend browse-jobs surfaces stay contract-safe by tracking known job IDs in browser session storage and resolving each row via `GET /jobs/{jobId}`.

### Technical Requirements

- Use the existing backend contract for `POST /projects`, `GET /projects`, `GET /projects/{projectId}`, `POST /projects/{projectId}/jobs`, and job retrieval flows.
- Keep refresh behavior local to query invalidation or refetch, not full-page reload.
- Preserve generic `404` handling for missing and cross-owner resources.
- Do not invent unsupported list endpoints; project/job browse UX must remain within the contract that exists today.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/app/(workspace)/projects/`
- `apps/web/src/app/(workspace)/jobs/`
- `apps/web/src/features/projects/`
- `apps/web/src/features/jobs/`
- `apps/web/src/shared/api/`
- `apps/web/tests/`

### Testing Requirements

- Verify create-project and create-job happy paths.
- Verify list refresh behavior after create.
- Verify no-leak `404` UI for missing or unauthorized routes.
- Verify status fields render exactly from backend payloads.
- Final verification target: `cd apps/web && make check`.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/1-2-create-and-read-owned-projects.md`
- `_bmad-output/implementation-artifacts/1-3-create-jobs-in-owned-projects-and-read-owned-job-status.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/1-2-create-and-read-owned-projects.md`
- `_bmad-output/implementation-artifacts/1-3-create-jobs-in-owned-projects-and-read-owned-job-status.md`

### Completion Notes List

- 2026-03-24: Created Story 7.3 artifact with project/job workspace scope and no-leak UI constraints.
- 2026-03-24: Captured list-refresh and ownership-boundary expectations for frontend implementation.
- 2026-03-24: Implemented shared project and job API/query modules, thin route files, owner-safe create flows, and contract-aligned project/job browse screens in `apps/web`.
- 2026-03-24: Added generic no-leak not-found UI, job status badges, browser-session recent-job tracking, and dynamic routes for project detail, project jobs, and job detail.
- 2026-03-24: Added unit tests for project/job contract calls, no-leak error detection, status rendering, and recent-jobs session storage behavior; passed `make lint`, `make test`, `make typecheck`, `make build`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/7-3-create-and-browse-owned-projects-and-jobs.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/app/(workspace)/jobs/[jobId]/page.tsx`
- `apps/web/src/app/(workspace)/jobs/page.tsx`
- `apps/web/src/app/(workspace)/projects/[projectId]/jobs/page.tsx`
- `apps/web/src/app/(workspace)/projects/[projectId]/page.tsx`
- `apps/web/src/app/(workspace)/projects/page.tsx`
- `apps/web/src/features/jobs/api.ts`
- `apps/web/src/features/jobs/hooks.ts`
- `apps/web/src/features/jobs/recent-jobs-session.ts`
- `apps/web/src/features/jobs/status.tsx`
- `apps/web/src/features/jobs/components/job-card.tsx`
- `apps/web/src/features/jobs/components/job-detail-screen.tsx`
- `apps/web/src/features/jobs/components/jobs-screen.tsx`
- `apps/web/src/features/jobs/components/project-jobs-screen.tsx`
- `apps/web/src/features/projects/api.ts`
- `apps/web/src/features/projects/hooks.ts`
- `apps/web/src/features/projects/components/project-card.tsx`
- `apps/web/src/features/projects/components/project-detail-screen.tsx`
- `apps/web/src/features/projects/components/projects-screen.tsx`
- `apps/web/src/shared/api/errors.ts`
- `apps/web/src/shared/lib/format-date.ts`
- `apps/web/src/shared/ui/input.tsx`
- `apps/web/src/shared/ui/no-leak-not-found-state.tsx`
- `apps/web/tests/unit/jobs-api.test.tsx`
- `apps/web/tests/unit/projects-api.test.ts`
- `apps/web/tests/unit/recent-jobs-session.test.ts`

### Change Log

- 2026-03-24: Created Story 7.3 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-24: Implemented owned project and job browsing flows, including contract-safe recent-jobs browse semantics where the API lacks a global jobs list endpoint.
- 2026-03-24: Added no-leak resource states and contract-oriented tests, passed `make check`, and moved Story 7.3 to `done`.
