# Story 1.3: Create Jobs in Owned Projects and Read Owned Job Status

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to create jobs under my projects and read status for my own jobs,
so that I can manage processing safely within my workspace.

## Acceptance Criteria

1. Given an authenticated editor and owned project, when they create a job, then the job is created under that project and initial state is contract-compliant.
2. Given a job owned by another editor, when an editor requests its status, then access is denied and no job data is exposed.

## Tasks / Subtasks

- [ ] Implement owner-scoped job creation and read boundaries in service/repository layers (AC: 1, 2)
- [ ] Ensure `POST /projects/{projectId}/jobs` verifies project ownership via service/repository logic (no route-level business logic).
- [ ] Ensure created job persists `owner_id` from authenticated principal and starts with status `CREATED`.
- [ ] Add owner-scoped repository method for job lookup by `job_id` that returns `None` for cross-owner/nonexistent access.
- [ ] Implement owned job status endpoint with no-leak behavior (AC: 2)
- [ ] Add `GET /jobs/{jobId}` route protected by bearer auth and wired through job service.
- [ ] Ensure cross-owner and nonexistent job lookups both return identical `404 RESOURCE_NOT_FOUND` payload shape.
- [ ] Keep route handlers thin and delegate ownership checks to service/repository layer.
- [ ] Keep OpenAPI runtime contract alignment for implemented job endpoints (AC: 1, 2)
- [ ] Ensure `/openapi.json` includes `POST /projects/{projectId}/jobs` and `GET /jobs/{jobId}` with contract-compatible status sets.
- [ ] Ensure response schemas stay aligned with `Job` and no-leak not-found contract schema usage.
- [ ] Add tests for job ownership boundaries and status retrieval no-leak semantics (AC: 1, 2)
- [ ] Add API tests for create-job success under owned project and initial `CREATED` status.
- [ ] Add API tests for `GET /jobs/{jobId}` owned access success and cross-owner/nonexistent parity (`404 RESOURCE_NOT_FOUND`).
- [ ] Add unit tests for job service/repository owner-scoped create/get behavior.

## Dev Notes

### Developer Context Section

- Story 1.1 established bearer auth + callback-secret baseline; Story 1.2 established owner-scoped project read patterns.
- This story extends ownership enforcement to jobs and introduces owned job status retrieval.
- Keep scope focused on create/get ownership boundaries only; do not implement confirm-upload (`/jobs/{jobId}/confirm-upload`) in this story.

### Technical Requirements

- Endpoint contract scope for this story:
- `POST /projects/{projectId}/jobs` (create job in owned project)
- `GET /jobs/{jobId}` (get owned job status)
- `POST /projects/{projectId}/jobs` must only create jobs for projects owned by authenticated principal.
- `GET /jobs/{jobId}` must apply no-existence-leak behavior: return `404` for both unauthorized access and missing job.
- Use `principal.user_id` from auth dependency for all ownership checks.
- Job create response must remain contract-compliant with `Job` schema and initial `status=CREATED`.

### Architecture Compliance

- `spec/` is read-only; implementation must follow `spec/api/openapi.yaml`.
- No business logic in route functions; enforce ownership in service/repository layers.
- Reuse existing error handling via `ApiError` and no-leak policy (`RESOURCE_NOT_FOUND`).
- Keep changes narrow to story scope and avoid unrelated refactors.

### Library & Framework Requirements

- FastAPI dependency injection for auth principal and service wiring.
- Pydantic response models aligned with OpenAPI contract.
- Preserve adapter isolation and do not call provider SDKs in business logic.

### File Structure Requirements

- Suggested implementation targets:
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/main.py` (if OpenAPI response filtering updates are required)
- `apps/api/tests/test_jobs_ownership.py` (new) or extend relevant API tests

### Testing Requirements

- Add tests mapped to ACs before marking this story complete.
- Required checks:
- Create job succeeds only for owned project and returns `CREATED`.
- Cross-owner/nonexistent project on create returns no-leak `404` behavior.
- Owned `GET /jobs/{jobId}` returns job data for creator/owner only.
- Cross-owner and nonexistent `GET /jobs/{jobId}` both return identical `404 RESOURCE_NOT_FOUND` shape.
- Existing Story 1.1 and 1.2 tests remain green (no regressions).
- Verification gates in `apps/api` must pass: `make lint`, `make test`, `make check`.

### Previous Story Intelligence

- Story 1.2 implemented owner-scoped repository/service patterns for projects; mirror those patterns for jobs.
- Story 1.2 review emphasized strict contract alignment for `/openapi.json` response status and schema references.
- Preserve no-leak behavior consistency: do not return distinguishable payloads/status for unauthorized vs missing resources.

### Git Intelligence Summary

- Recent commits and story work show active hardening around no-leak behavior and OpenAPI contract parity.
- Prefer incremental modifications in existing route/service/repository modules over introducing parallel structures.
- Keep testing in the current unittest flow under `apps/api/tests`.

### Project Structure Notes

- No standalone architecture artifact exists under `_bmad-output/planning-artifacts/`; implementation guardrails derive from OpenAPI, PRD, epics, project context, and completed stories.
- Maintain the established package layout (`routes/`, `services/`, `repositories/`, `schemas/`, `tests/`).

### References

- `spec/api/openapi.yaml` (`/projects/{projectId}/jobs`, `/jobs/{jobId}`, `Job`, `NoLeakNotFoundError`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 1, Story 1.3)
- `_bmad-output/planning-artifacts/prd.md` (FR-003, FR-004)
- `_bmad-output/project-context.md` (Spec Is Law, ownership/security model, route thinness)
- `spec/acceptance/tasks_codex_v1.md` (Task 05 scope and acceptance)
- `_bmad-output/implementation-artifacts/1-1-authenticate-api-requests-as-editor.md`
- `_bmad-output/implementation-artifacts/1-2-create-and-read-owned-projects.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story scope constrained to owned job creation and owned job status retrieval, with no-leak and contract-alignment guardrails emphasized.

### File List

- `_bmad-output/implementation-artifacts/1-3-create-jobs-in-owned-projects-and-read-owned-job-status.md`
