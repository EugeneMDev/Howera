# Story 1.2: Create and Read Owned Projects

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to create projects and read only my own projects,
so that my workspace is isolated from other users.

## Acceptance Criteria

1. Given an authenticated editor, when they create a project, then the project is persisted with that editor as owner and response fields match OpenAPI contract.
2. Given two editors with separate projects, when one editor lists or retrieves projects, then only that editor's projects are returned and cross-owner project access is denied.

## Tasks / Subtasks

- [ ] Implement project ownership persistence and repository boundaries (AC: 1, 2)
- [ ] Ensure project records store `owner_id` from authenticated principal at creation time.
- [ ] Implement owner-scoped repository methods for list/get operations and no direct storage logic in routes.
- [ ] Implement project read endpoints with ownership enforcement (AC: 2)
- [ ] Add `GET /projects` to return only projects owned by current principal.
- [ ] Add `GET /projects/{projectId}` with ownership check and no-existence-leak `404` behavior.
- [ ] Keep route handlers thin and delegate ownership checks to service/repository layer.
- [ ] Align create-project behavior with ownership requirements (AC: 1)
- [ ] Ensure `POST /projects` persists owner association and returns only contract fields (`id`, `name`, `created_at`).
- [ ] Ensure cross-owner access cannot leak existence details through status/body differences.
- [ ] Add tests for ownership boundaries and no-leak semantics (AC: 1, 2)
- [ ] Add API tests for create + list + get under two different users.
- [ ] Add API tests that unauthorized/nonexistent project reads both return the same `404 RESOURCE_NOT_FOUND` shape.
- [ ] Add unit tests for project service/repository owner-scoping logic.

## Dev Notes

### Developer Context Section

- Story 1.1 is complete and provides the auth foundation (`get_authenticated_principal`, normalized `AuthPrincipal`, and callback-secret isolation).
- This story should build on that baseline by adding ownership filtering and no-leak semantics for project reads.
- Keep scope focused on project ownership and retrieval boundaries; do not expand into job-level ownership yet (Story 1.3).

### Technical Requirements

- Endpoint contract scope for this story:
- `POST /projects` (create owned project)
- `GET /projects` (list owned projects)
- `GET /projects/{projectId}` (get owned project)
- `GET /projects/{projectId}` must return `404` for both unauthorized access and missing project (no-existence-leak policy).
- Error payload for no-leak behavior must remain consistent with contract shape (`RESOURCE_NOT_FOUND`).
- Preserve authenticated principal propagation from Story 1.1 and consume `principal.user_id` for ownership checks.

### Architecture Compliance

- `spec/` is read-only; implementation must follow `spec/api/openapi.yaml`.
- Keep business logic out of route functions; enforce ownership in service/repository layer.
- Maintain provider isolation (no auth provider SDK calls outside adapter layer).
- Keep changes narrow to this story's ownership/read behavior and avoid unrelated refactors.

### Library & Framework Requirements

- FastAPI dependency injection for auth principal and service wiring.
- Pydantic response models aligned with contract fields.
- API errors should use existing structured error handling (`ApiError`) and no-leak policy where specified.

### File Structure Requirements

- Suggested implementation targets:
- `apps/api/app/routes/projects.py`
- `apps/api/app/services/projects.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/project.py`
- `apps/api/tests/test_projects_ownership.py` (or extend existing project/auth API tests)
- Keep internal callback route (`/internal/jobs/{jobId}/status`) untouched for this story.

### Testing Requirements

- Add tests mapped to ACs before marking this story complete.
- Required checks:
- Creating a project stores ownership (`owner_id`) based on authenticated principal.
- Listing projects for user A excludes user B's projects.
- Retrieving user B's project as user A returns contract no-leak `404` shape.
- Retrieving a nonexistent project returns the same `404` shape as cross-owner access.
- Existing Story 1.1 auth behavior remains green (no regressions).

### Previous Story Intelligence

- Reuse auth dependency and context propagation patterns from Story 1.1 rather than introducing new auth paths.
- Follow the established pattern of service-layer ownership checks and centralized `ApiError` responses.
- Keep OpenAPI/runtime behavior aligned; avoid documenting statuses that are not returned at runtime.

### Git Intelligence Summary

- Recent commits indicate active work on no-leak 404 semantics and API contract alignment.
- Prefer incremental updates to existing modules over introducing parallel structures.
- Maintain current test command flow (`make lint`, `make test`, `make check`) in `apps/api`.

### Project Structure Notes

- No dedicated architecture document was found in `_bmad-output/planning-artifacts/`; architectural guardrails are sourced from project context, OpenAPI, PRD, epics, and prior implemented story.
- Continue using the existing app package layout (`routes/`, `services/`, `repositories/`, `schemas/`) established in Story 1.1.

### References

- `spec/api/openapi.yaml` (`/projects`, `/projects/{projectId}`, `Project`, `NoLeakNotFoundError`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 1, Story 1.2)
- `_bmad-output/planning-artifacts/prd.md` (FR-001, FR-002)
- `_bmad-output/project-context.md` (Spec Is Law, Security Model, architecture invariants)
- `spec/acceptance/tasks_codex_v1.md` (global rules, Task 03 ownership boundaries, Task 04 no-leak behavior)
- `_bmad-output/implementation-artifacts/1-1-authenticate-api-requests-as-editor.md` (completed auth baseline and implementation patterns)

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- No architecture artifact was available in planning artifacts; story guardrails were derived from OpenAPI, PRD, epics, project context, and Story 1.1 implementation learnings.

### File List

- `_bmad-output/implementation-artifacts/1-2-create-and-read-owned-projects.md`
