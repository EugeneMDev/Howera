# Story 4.1: Retrieve Transcript Segments for Job

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want transcript segments for my job,
so that I can ground edits and regeneration on source timing and text.

## Acceptance Criteria

1. Given an authenticated editor requesting transcript for an owned job in allowed states (`TRANSCRIPT_READY`, `GENERATING`, `DRAFT_READY`, `EDITING`, `EXPORTING`, `DONE`, `FAILED`), when transcript retrieval is called, then API returns contract-compliant transcript segments ordered by `start_ms` and applies pagination and size policy (`limit`, `cursor`, max page size).
2. Given transcript retrieval is requested for non-owned or nonexistent resource, when authorization and resource checks run, then API uses no-existence-leak policy (`404` for both cases) and no ownership details are exposed.
3. Given job is in a state where transcript is not yet available, when retrieval is requested, then API returns contract-defined availability error (`409 TRANSCRIPT_NOT_READY`) and response/logs exclude raw transcript beyond explicitly returned transcript payload.

## Tasks / Subtasks

- [x] Implement `GET /jobs/{jobId}/transcript` route and service boundary (AC: 1, 2, 3)
- [x] Add transcript endpoint handler in jobs routes with authenticated owner-scoped behavior.
- [x] Keep route thin; transcript state gating and pagination logic must remain in service/repository boundaries.
- [x] Enforce no-existence-leak ownership semantics (AC: 2)
- [x] Return `404 RESOURCE_NOT_FOUND` for missing and non-owned job uniformly.
- [x] Ensure no state mutation side effects on `404` paths.
- [x] Enforce transcript availability state gating (AC: 1, 3)
- [x] Allow transcript retrieval only for states: `TRANSCRIPT_READY`, `GENERATING`, `DRAFT_READY`, `EDITING`, `EXPORTING`, `DONE`, `FAILED`.
- [x] Return `409` contract error with code `TRANSCRIPT_NOT_READY` for non-allowed states and include `details.current_status`.
- [x] Preserve secure logging boundaries for transcript retrieval paths.
- [x] Implement transcript page contract behavior (AC: 1)
- [x] Add schema support for `TranscriptSegment` and `TranscriptPage` contract shape.
- [x] Support query params: `limit` (default `200`, max `500`, min `1`) and `cursor`.
- [x] Return transcript segments ordered by `start_ms` and include `next_cursor` semantics.
- [x] Add AC-mapped tests + contract assertions (AC: 1, 2, 3)
- [x] Add API tests for allowed-state retrieval success with pagination behavior and ordering.
- [x] Add API tests for non-owned and missing job no-leak `404`.
- [x] Add API tests for disallowed-state retrieval `409 TRANSCRIPT_NOT_READY`.
- [x] Add unit tests for pagination/state-gating helper behavior and no-side-effect reject paths.
- [x] Update OpenAPI contract assertions for `/jobs/{jobId}/transcript` response set (`200/404/409`) and schema refs.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Enforce transcript `limit` policy without leaking FastAPI `422` responses; invalid `limit` must remain within the endpoint contract response set and use contract-safe error shape. [apps/api/app/routes/jobs.py:70, apps/api/app/main.py:44]
- [x] [AI-Review][HIGH] Align `/jobs/{jobId}/transcript` OpenAPI `409` schema to contract `#/components/schemas/Error` (not `ErrorResponse`). [apps/api/app/routes/jobs.py:64, apps/api/app/main.py:121]
- [x] [AI-Review][MEDIUM] Align transcript query `cursor` OpenAPI schema to contract `type: string` (non-nullable optional parameter). [apps/api/app/main.py:128, apps/api/tests/test_auth_middleware.py:136]
- [x] [AI-Review][MEDIUM] Add a production path that persists transcript segments for retrieval (current implementation only reads `transcript_segments_by_job` populated by tests). [apps/api/app/repositories/memory.py:265, apps/api/tests/test_jobs_ownership.py:815]

## Dev Notes

### Developer Context Section

- Epic 3 established owner-scoped no-leak behavior, FSM-gated lifecycle checks, and callback-driven transcript artifact persistence (`manifest.transcript_uri`).
- Existing API patterns for Jobs routes/services should be reused to keep ownership/security/error behavior consistent.
- Transcript endpoint is read-only and must not regress write-path idempotency and transition invariants.

### Technical Requirements

- Endpoint in scope: `GET /jobs/{jobId}/transcript`.
- Response contract:
  - `200` with `TranscriptPage` (`items[]`, `limit`, `next_cursor`).
  - `404` with `NoLeakNotFoundError` for missing/non-owned job.
  - `409` with `Error` code `TRANSCRIPT_NOT_READY` when job state does not permit transcript retrieval.
- Transcript segments must conform to `TranscriptSegment` (`start_ms`, `end_ms`, `text`).
- Query params must follow contract: `limit` default `200`, max `500`, min `1`; `cursor` optional.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Preserve no-existence-leak behavior on editor-facing resources.
- Keep route handlers thin and place business rules in service/repository layers.
- Do not introduce direct provider SDK coupling in business logic.
- Preserve secure logging rules: no transcript leakage outside explicit API payload.

### Library & Framework Requirements

- FastAPI request/response handling with Pydantic schemas for contract-aligned responses.
- Reuse existing `ApiError` error-shaping patterns for `404` and `409`.
- No new external dependencies are expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/main.py` (OpenAPI response-set shaping, if needed)
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Testing Requirements

- Validate successful transcript retrieval for each allowed state path.
- Validate transcript ordering by `start_ms` and pagination behavior for `limit` + `cursor`.
- Validate non-owned/missing resource no-leak `404`.
- Validate disallowed states return `409 TRANSCRIPT_NOT_READY` with `details.current_status`.
- Validate reject paths do not mutate persisted job/state records.
- Validate `/openapi.json` includes `/jobs/{jobId}/transcript` with `200/404/409` and expected schema references.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 3.6 reinforced run/retry dispatch semantics and regression-oriented tests in `test_jobs_ownership.py`; mirror this style for transcript gating/pagination and no-side-effect checks.
- Story 3.x established careful OpenAPI response assertions in `test_auth_middleware.py`; preserve strict response-code/schema checks.

### Git Intelligence Summary

- Existing implementation patterns are stable for:
  - owner-scoped no-leak access checks
  - structured `ApiError` responses
  - tests that assert write-count side effects
- Story 4.1 should extend these patterns with minimal diff and no unrelated refactors.

### Project Structure Notes

- Current codebase has no transcript retrieval endpoint implemented yet; this story introduces the first transcript read API.
- Keep implementation focused on transcript endpoint + schema/service/test contract alignment only.

### References

- `spec/api/openapi.yaml` (`/jobs/{jobId}/transcript`, `TranscriptSegment`, `TranscriptPage`, `TRANSCRIPT_NOT_READY`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.1)
- `spec/acceptance/tasks_codex_v1.md` (Task 08)
- `_bmad-output/project-context.md` (ownership/security/FSM invariants)
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`
- `spec/acceptance/tasks_codex_v1.md`
- `_bmad-output/project-context.md`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Completion Notes List

- 2026-02-28: Created Story 4.1 artifact with contract-accurate transcript retrieval requirements, AC-mapped tasks, and implementation guardrails.
- 2026-02-28: Marked Story 4.1 as `ready-for-dev` in sprint tracking and moved Epic 4 to `in-progress`.
- 2026-03-01: Implemented `GET /jobs/{jobId}/transcript` with owner-scoped no-leak `404`, allowed-state gating, `409 TRANSCRIPT_NOT_READY`, and cursor-based pagination over ordered transcript segments.
- 2026-03-01: Added schema/repository support (`TranscriptSegment`, `TranscriptPage`, in-memory transcript segment storage) and AC-mapped API/service tests plus OpenAPI assertions.
- 2026-03-01: Verification passed in `apps/api` with `make lint`, `make test`, and `make check` (91 tests passing).
- 2026-03-01: Senior code review completed with changes requested; story moved back to `in-progress` with AI review follow-up action items.
- 2026-03-01: Resolved all AI review follow-ups (contract-safe transcript validation/no-422 leakage, OpenAPI schema alignment for `409` + `cursor`, and callback-driven transcript segment persistence), reran full quality gates, and advanced story to `done`.

### File List

- `_bmad-output/implementation-artifacts/4-1-retrieve-transcript-segments-for-job.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_internal_callback_transactions.py`

### Change Log

- 2026-02-28: Created Story 4.1 artifact and moved status from `backlog` to `ready-for-dev`.
- 2026-02-28: Updated Epic 4 status from `backlog` to `in-progress` after creating first story in epic.
- 2026-03-01: Implemented transcript retrieval endpoint with state gating, pagination, no-leak behavior, and OpenAPI/test coverage; moved story status to `review`.
- 2026-03-01: Senior code review completed with changes requested; added AI review follow-up tasks and moved status to `in-progress`.
- 2026-03-01: Applied all code-review fixes, expanded transcript/callback regression coverage, reran quality gates (94 tests), and moved status to `done`.

## Senior Developer Review (AI)

### Review Date

2026-03-01

### Reviewer

GPT-5.3-Codex

### Outcome

Approve

### Findings Summary

- 0 High, 0 Medium, 0 Low remaining.

### Findings and Resolutions

- [x] [HIGH] Invalid transcript `limit` values return FastAPI validation `422`, which is outside this endpoint’s contract response set (`200/404/409`).
  - Resolution: Removed hard query-bound validation from route, enforced limit policy in service with `409 VALIDATION_ERROR`, and added transcript-path request-validation remap to keep malformed query cases within contract status set.
  - Evidence: `apps/api/app/routes/jobs.py:70`, `apps/api/app/services/jobs.py:365-387`, `apps/api/app/main.py:44-47`, `apps/api/tests/test_jobs_ownership.py` (`test_get_transcript_invalid_limit_returns_409_validation_error_without_side_effects`).
- [x] [HIGH] `/jobs/{jobId}/transcript` OpenAPI `409` response is emitted as `#/components/schemas/ErrorResponse` instead of contract `#/components/schemas/Error`.
  - Resolution: Added explicit `Error` schema model and enforced transcript `409` OpenAPI reference to `#/components/schemas/Error`.
  - Evidence: `apps/api/app/schemas/error.py:18`, `apps/api/app/routes/jobs.py:64`, `apps/api/app/main.py:121`, `apps/api/tests/test_auth_middleware.py:125`.
- [x] [MEDIUM] Transcript `cursor` parameter is documented as nullable (`string | null`) while contract defines `type: string` and optional presence.
  - Resolution: Applied transcript OpenAPI parameter normalization so `cursor` is emitted as non-nullable `type: string`.
  - Evidence: `apps/api/app/main.py:128`, `apps/api/tests/test_auth_middleware.py:136`.
- [x] [MEDIUM] Transcript retrieval reads from `transcript_segments_by_job`, but no production write path populates it (setter currently used only by tests).
  - Resolution: Added callback artifact update handling for `transcript_segments` with transactional rollback guarantees, and covered end-to-end retrieval from callback-persisted segments.
  - Evidence: `apps/api/app/repositories/memory.py:265-395`, `apps/api/tests/test_jobs_ownership.py` (`test_get_transcript_reads_segments_persisted_from_internal_callback`), `apps/api/tests/test_internal_callback_transactions.py` (`test_callback_failpoint_rolls_back_all_side_effects`).
