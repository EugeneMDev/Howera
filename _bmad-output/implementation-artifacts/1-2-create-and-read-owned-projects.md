# Story 1.2: Create and Read Owned Projects

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to create projects and read only my own projects,
so that my workspace is isolated from other users.

## Acceptance Criteria

1. Given an authenticated editor, when they create a project, then the project is persisted with that editor as owner and response fields match OpenAPI contract.
2. Given two editors with separate projects, when one editor lists or retrieves projects, then only that editor's projects are returned and cross-owner project access is denied.

## Tasks / Subtasks

- [x] Implement project ownership persistence and repository boundaries (AC: 1, 2)
- [x] Ensure project records store `owner_id` from authenticated principal at creation time.
- [x] Implement owner-scoped repository methods for list/get operations and no direct storage logic in routes.
- [x] Implement project read endpoints with ownership enforcement (AC: 2)
- [x] Add `GET /projects` to return only projects owned by current principal.
- [x] Add `GET /projects/{projectId}` with ownership check and no-existence-leak `404` behavior.
- [x] Keep route handlers thin and delegate ownership checks to service/repository layer.
- [x] Align create-project behavior with ownership requirements (AC: 1)
- [x] Ensure `POST /projects` persists owner association and returns only contract fields (`id`, `name`, `created_at`).
- [x] Ensure cross-owner access cannot leak existence details through status/body differences.
- [x] Add tests for ownership boundaries and no-leak semantics (AC: 1, 2)
- [x] Add API tests for create + list + get under two different users.
- [x] Add API tests that unauthorized/nonexistent project reads both return the same `404 RESOURCE_NOT_FOUND` shape.
- [x] Add unit tests for project service/repository owner-scoping logic.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Align `GET /projects/{projectId}` `404` response schema to OpenAPI `NoLeakNotFoundError` instead of generic `ErrorResponse` so the runtime contract matches `spec/api/openapi.yaml`. [apps/api/app/routes/projects.py:45]
- [x] [AI-Review][MEDIUM] Remove undocumented `401` response codes from runtime OpenAPI for `GET /projects` and `GET /projects/{projectId}` (or update spec in a separate task) to maintain strict contract-first parity. [apps/api/app/main.py:18]
- [x] [AI-Review][MEDIUM] Add OpenAPI contract assertions for response schema refs (not only status code sets), including `GET /projects/{projectId}` `404` -> `NoLeakNotFoundError`, to prevent silent schema drift. [apps/api/tests/test_auth_middleware.py:74]

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

- Implemented owner-scoped project access in repository and service layers (`list_projects_for_owner`, `get_project_for_owner`, `ProjectService.list_projects`, `ProjectService.get_project`) while keeping route handlers thin.
- Added `GET /api/v1/projects` and `GET /api/v1/projects/{projectId}` with bearer-auth principal scoping and no-leak `404 RESOURCE_NOT_FOUND` behavior for cross-owner and nonexistent project access.
- Kept create-project ownership behavior aligned by persisting `owner_id` from authenticated principal and returning only contract fields (`id`, `name`, `created_at`).
- Added ownership API tests and unit tests covering: create/list/get under separate users, identical no-leak `404` shape for unauthorized vs missing resources, and owner-scoping logic at service/repository level.
- Updated OpenAPI response-code filtering assertions for implemented project read endpoints and verified `/openapi.json` includes expected paths.
- Verification completed in `apps/api`: `make lint`, `make test`, and `make check` all passed on 2026-02-23.
- Resolved all code-review findings: introduced a dedicated `NoLeakNotFoundError` schema model, aligned `GET /projects/{projectId}` `404` response docs to that schema, removed undocumented read-endpoint `401` response codes from filtered OpenAPI, and added schema-ref assertions in OpenAPI tests.

### File List

- `apps/api/app/main.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/routes/projects.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/services/projects.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_projects_ownership.py`
- `_bmad-output/implementation-artifacts/1-2-create-and-read-owned-projects.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-02-23: Completed Story 1.2 implementation for owned-project creation/read boundaries, no-leak `404` enforcement, and ownership test coverage; story moved to `review`.
- 2026-02-23: Senior code review completed with Changes Requested; added review follow-up items and moved story to `in-progress`.
- 2026-02-23: Applied all HIGH/MEDIUM review fixes, re-validated test/lint/check gates, and moved story to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-02-23

### Outcome

- Approved

### Summary

- Ownership enforcement and no-leak runtime behavior are implemented and tested, but the documented API contract is not fully aligned with `spec/api/openapi.yaml`.
- The main risk is schema/status drift in generated OpenAPI for newly added read endpoints, which violates the repository's contract-first rules.

### Severity Breakdown

- High: 1
- Medium: 2
- Low: 0

### Action Items

- [x] [HIGH] Use the contract `NoLeakNotFoundError` schema for `GET /projects/{projectId}` `404` response documentation instead of generic `ErrorResponse`. [apps/api/app/routes/projects.py:45]
- [x] [MEDIUM] Keep runtime `/openapi.json` status codes for project read endpoints strictly aligned to `spec/api/openapi.yaml` (remove `401` from filtered response maps unless spec changes separately). [apps/api/app/main.py:18]
- [x] [MEDIUM] Strengthen OpenAPI tests to assert response schema refs for project read endpoints, especially `404` no-leak shape schema. [apps/api/tests/test_auth_middleware.py:74]

### Follow-up Resolution

- 2026-02-23: All HIGH/MEDIUM action items resolved and re-validated with `make check`; story approved.
