# Story 2.1: Confirm Job Upload with Video URI

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to confirm a job upload by submitting `video_uri`,
so that the system can accept the job for processing.

## Acceptance Criteria

1. Given an authenticated editor with an owned eligible job and valid `video_uri`, when confirm-upload is requested, then job transitions to `UPLOADED` via FSM, `artifact_manifest.video_uri` is stored exactly as submitted, and the response matches the OpenAPI contract.
2. Given confirm-upload is called again with the same `video_uri`, when the request is processed, then processing is idempotent, no duplicate writes occur, and no additional state transitions occur.
3. Given confirm-upload is called with a different `video_uri` for the same job, when the request is processed, then the API returns a contract-defined conflict error and no mutation occurs.

## Tasks / Subtasks

- [x] Implement confirm-upload API contract path and schema wiring (AC: 1, 2, 3)
- [x] Add `POST /jobs/{jobId}/confirm-upload` route with auth principal dependency and no route-level business logic.
- [x] Add/align request and response schemas with contract (`ConfirmUploadRequest`, `ConfirmUploadResponse`).
- [x] Ensure runtime OpenAPI includes contract response set for confirm-upload (`200`, `404`, `409`) and conflict `oneOf` (`FsmTransitionError`, `VideoUriConflictError`).
- [x] Implement FSM-governed status mutation and artifact manifest persistence (AC: 1)
- [x] Enforce owner-scoped job lookup with no-leak `404` parity for unauthorized vs missing jobs.
- [x] Validate transition to `UPLOADED` via `domain/job_fsm.ensure_transition` before mutation.
- [x] Persist `artifact_manifest.video_uri` exactly as provided on first accepted confirm-upload.
- [x] Keep terminal-state and forbidden-transition behavior contract-safe via existing FSM error mapping.
- [x] Implement idempotency and conflict semantics for `video_uri` (AC: 2, 3)
- [x] Replay same `video_uri` returns success with `replayed=true` and does not increment writes or re-transition state.
- [x] Different `video_uri` for same job returns `409 VIDEO_URI_CONFLICT` with contract details and no mutation.
- [x] Add API/unit regression tests for confirm-upload behavior (AC: 1, 2, 3)
- [x] Test first confirm-upload success (`UPLOADED`, manifest persisted, contract response shape).
- [x] Test same-URI replay idempotency (no extra writes/state transition, contract replay response).
- [x] Test conflicting URI returns `409 VIDEO_URI_CONFLICT` with `current_video_uri` and `submitted_video_uri`.
- [x] Test cross-owner and nonexistent job parity returns no-leak `404 RESOURCE_NOT_FOUND`.
- [x] Verify quality gates and contract safety (AC: 1, 2, 3)
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.
- [x] Validate `/openapi.json` contains confirm-upload path and response schemas that match `spec/api/openapi.yaml`.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Resolve contract drift where malformed `confirm-upload` payload currently returns runtime `422`, which is outside the documented endpoint response set (`200/404/409`). [apps/api/app/main.py:106]
- [x] [AI-Review][MEDIUM] Add explicit regression coverage for malformed `confirm-upload` payload behavior so future contract/status drift is caught automatically. [apps/api/tests/test_jobs_ownership.py:103]
- [x] [AI-Review][MEDIUM] Reconcile story File List with actual git change set (or isolate unrelated pending edits) to keep review traceability accurate for this story. [_bmad-output/implementation-artifacts/2-1-confirm-job-upload-with-video-uri.md:133]

## Dev Notes

### Developer Context Section

- Story 1.3 implemented owner-scoped job read/create boundaries and no-leak semantics.
- Story 1.5 completed secure logging hardening; preserve those guarantees while implementing confirm-upload.
- This story introduces upload confirmation idempotency and `video_uri` conflict semantics before workflow dispatch (Story 2.2).

### Technical Requirements

- Contract endpoint: `POST /jobs/{jobId}/confirm-upload`.
- Request body requires `video_uri` (string).
- Response returns `ConfirmUploadResponse` (`job`, `replayed`).
- Conflict response must use contract-defined `VideoUriConflictError` shape.
- First acceptance persists `artifact_manifest.video_uri` exactly and transitions job to `UPLOADED` via FSM.
- Same URI replay is no-op success; different URI returns conflict with no mutation.

### Architecture Compliance

- `spec/` is source of truth and read-only.
- All status transitions must go through `domain/job_fsm.ensure_transition`.
- Preserve no-leak behavior and owner-scoped checks in service/repository layers.
- Keep routes thin; business logic in service/domain/repository boundaries.

### Library & Framework Requirements

- FastAPI + Pydantic models for request/response bodies.
- Reuse existing `ApiError` and contract error schema patterns.
- No external dependency additions are expected for this story.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/main.py` (only if OpenAPI response filtering requires contract alignment)
- `apps/api/tests/test_jobs_ownership.py` and/or `apps/api/tests/test_auth_middleware.py`

### Testing Requirements

- Add AC-mapped tests for first success, replay idempotency, conflict mismatch, and no-leak parity.
- Assert no duplicate write counters on replay and no mutation on conflict.
- Keep existing tests green; avoid regressions in story 1.x behavior.
- Final verification gate: `make lint`, `make test`, `make check` in `apps/api`.

### Previous Story Intelligence

- Prior stories frequently surfaced OpenAPI response/schema drift; explicitly assert schema refs in tests.
- Existing job ownership/no-leak behavior should be reused, not re-implemented in route handlers.
- Callback and logging hardening from Story 1.4/1.5 should remain unchanged by this intake story.

### Git Intelligence Summary

- Epic 1 delivered auth, ownership, callback, and logging guardrails in incremental changes.
- Keep this change set focused on confirm-upload FSM/idempotency logic and tests.

### Project Structure Notes

- No standalone architecture artifact is currently present in `_bmad-output/planning-artifacts/`; use OpenAPI + PRD + FSM spec + existing implemented patterns.
- Continue using the established `routes/services/repositories/schemas/tests` structure in `apps/api`.

### References

- `spec/api/openapi.yaml` (`ConfirmUploadRequest`, `ConfirmUploadResponse`, `VideoUriConflictError`, `/jobs/{jobId}/confirm-upload`)
- `spec/domain/job_fsm.md` (allowed transitions to `UPLOADED`, terminal immutability, transition enforcement)
- `spec/acceptance/tasks_codex_v1.md` (confirm-upload idempotency and conflict acceptance)
- `_bmad-output/planning-artifacts/epics.md` (Epic 2, Story 2.1)
- `_bmad-output/planning-artifacts/prd.md` (FR-006, FR-007, FR-008)
- `_bmad-output/implementation-artifacts/1-3-create-jobs-in-owned-projects-and-read-owned-job-status.md`
- `_bmad-output/implementation-artifacts/1-5-enforce-secure-logging-boundaries.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`
- `spec/domain/job_fsm.md`

### Completion Notes List

- Implemented `POST /jobs/{jobId}/confirm-upload` with owner-scoped access, FSM transition validation, and manifest `video_uri` persistence.
- Added confirm-upload idempotency behavior: same `video_uri` replay returns `200` with `replayed=true` and no additional writes.
- Added conflict behavior for differing `video_uri` values with contract-shaped `409 VIDEO_URI_CONFLICT` details and no mutation.
- Updated runtime OpenAPI filtering and explicit confirm-upload `409` oneOf schema alignment.
- Added API and unit tests for confirm-upload success, replay idempotency, conflict, and no-leak 404 parity.
- Verification completed in `apps/api`: `make lint`, `make test`, and `make check` all passed on 2026-02-26.
- ✅ Resolved review finding [HIGH]: malformed confirm-upload payloads are now normalized to contract-safe `409 VALIDATION_ERROR` instead of runtime `422`.
- ✅ Resolved review finding [MEDIUM]: added explicit regression test for malformed confirm-upload payload behavior with no-mutation assertion.
- ✅ Resolved review finding [MEDIUM]: reconciled story file scope; File List intentionally tracks Story 2.1 files while pre-existing unrelated pending edits remain scoped to Story 1.5 artifacts/code.

### File List

- `_bmad-output/implementation-artifacts/2-1-confirm-job-upload-with-video-uri.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/main.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-02-26: Implemented Story 2.1 confirm-upload FSM/idempotency/conflict behavior with contract-aligned OpenAPI and tests; story moved to `review`.
- 2026-02-26: Senior code review completed with changes requested; follow-up contract and coverage items added and story moved to `in-progress`.
- 2026-02-26: Addressed all code-review follow-ups (validation contract mapping, malformed-payload regression coverage, file-list traceability note), re-ran quality gates, and moved story back to `review`.
- 2026-02-26: Re-review completed with no remaining HIGH/MEDIUM issues; story moved to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-02-26

### Outcome

- Changes Requested

### Summary

- Core confirm-upload behavior (FSM transition, replay idempotency, conflict semantics, no-leak ownership) is implemented and validated.
- Remaining issue: malformed request payloads currently escape the contract response envelope and return `422` at runtime.

### Severity Breakdown

- High: 1
- Medium: 2
- Low: 0

### Action Items

- [x] [HIGH] Resolve contract drift where malformed `confirm-upload` payload currently returns runtime `422`, which is outside the documented endpoint response set (`200/404/409`). [apps/api/app/main.py:106]
- [x] [MEDIUM] Add explicit regression coverage for malformed `confirm-upload` payload behavior so future contract/status drift is caught automatically. [apps/api/tests/test_jobs_ownership.py:103]
- [x] [MEDIUM] Reconcile story File List with actual git change set (or isolate unrelated pending edits) to keep review traceability accurate for this story. [_bmad-output/implementation-artifacts/2-1-confirm-job-upload-with-video-uri.md:133]

### Final Re-Review (AI) - 2026-02-26

#### Outcome

- Approved

#### Summary

- Confirm-upload contract behavior is implemented with FSM, idempotent replay, and conflict no-mutation guarantees.
- Malformed payload handling now stays within the endpoint response contract and is covered by regression tests.
- Quality gates pass (`make lint`, `make test`, `make check`).
