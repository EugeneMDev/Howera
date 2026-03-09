# Story 1.4: Validate Internal Callback Secret

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a platform operator,
I want internal status callbacks to require a shared secret,
so that only trusted orchestrator calls can mutate internal status.

## Acceptance Criteria

1. Given an internal callback request without valid `X-Callback-Secret`, when the endpoint is invoked, then the API rejects the request and no status mutation is performed.
2. Given a callback with valid secret, when payload validation succeeds, then the callback is accepted for domain processing and the request follows normal FSM and idempotency processing.

## Tasks / Subtasks

- [x] Enforce callback-secret authentication on internal callback endpoint (AC: 1, 2)
- [x] Ensure `/internal/jobs/{jobId}/status` uses `X-Callback-Secret` security scheme and rejects missing/invalid secret with contract `401`.
- [x] Use constant-time secret comparison logic and centralized dependency wiring from route dependencies.
- [x] Ensure auth failure occurs before any callback domain mutation side effects.
- [x] Wire valid callback requests to domain processing entrypoint (AC: 2)
- [x] Keep route handler thin; delegate callback processing to service/domain layer (or clear stub boundary) for FSM/idempotency handling.
- [x] Preserve no-leak behavior for unknown/non-owned jobs as defined by contract (`404 RESOURCE_NOT_FOUND`) when callback processing runs.
- [x] Keep contract alignment for callback route responses and schemas (AC: 1, 2)
- [x] Verify `/openapi.json` callback path includes response set `200/204/401/404/409` and uses `internalCallbackSecret`.
- [x] Ensure error payloads are contract-compatible and do not introduce undocumented fields/statuses.
- [x] Add tests for callback-secret gate and no-side-effect behavior (AC: 1, 2)
- [x] Add API tests for missing and invalid callback secret returning `401`.
- [x] Add API test confirming valid callback secret reaches processing path and returns contract status.
- [x] Add side-effect guard test proving invalid callback-secret requests do not mutate job state/store counters.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Implement actual callback domain handling for valid-secret requests (event processing path with FSM/idempotency semantics) instead of a no-op service stub so AC #2 is truly satisfied. [apps/api/app/services/internal_callbacks.py:12]
- [x] [AI-Review][MEDIUM] Stop classifying callback request-body validation failures as `401 UNAUTHORIZED`; this conflates auth and payload validation and can mask callback-contract error handling paths. [apps/api/app/main.py:70]
- [x] [AI-Review][MEDIUM] Restrict or encapsulate unscoped `get_job` repository access to avoid accidental use in editor-facing code paths that require owner-scoped lookups. [apps/api/app/repositories/memory.py:85]
- [x] [AI-Review][HIGH] Align callback request schema with contract by adding optional fields (`actor_type`, `artifact_updates`, `failure_code`, `failure_message`, `failed_stage`) to `StatusCallbackRequest`; current model rejects contract-valid payload shapes. [apps/api/app/schemas/internal.py:10]
- [x] [AI-Review][MEDIUM] Use contract-specific `409` schema modeling on internal callback route (FSM/order/payload-mismatch oneOf) instead of generic `ErrorResponse` to avoid OpenAPI contract drift. [apps/api/app/routes/internal.py:23]
- [x] [AI-Review][MEDIUM] Tighten callback ordering guard to reject non-monotonic timestamps (`<=` latest) so equal-timestamp events cannot bypass ordering policy. [apps/api/app/services/internal_callbacks.py:54]

## Dev Notes

### Developer Context Section

- Story 1.1 introduced callback-secret dependency and callback route skeleton.
- Story 1.3 reinforced contract-first response parity and no-leak behavior patterns.
- This story hardens callback-secret enforcement as a non-bypassable gate before callback state mutation.

### Technical Requirements

- Endpoint in scope: `POST /internal/jobs/{jobId}/status`.
- Header contract: `X-Callback-Secret` (`internalCallbackSecret` security scheme).
- Missing/invalid callback secret must return `401` with contract error shape.
- Valid secret request must continue to callback processing path; payload and status handling remains contract-driven.
- No mutation may occur when callback secret validation fails.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep route handlers thin; business behavior belongs in service/domain layers.
- FSM transition validation and callback idempotency are mandatory and must remain centralized in domain logic when implemented.
- Do not introduce provider SDK coupling in callback/auth flow.

### Library & Framework Requirements

- FastAPI security dependency with `APIKeyHeader` for callback secret.
- Pydantic request/response models aligned with OpenAPI callback schemas.
- Preserve global exception handling shape for `ApiError`.

### File Structure Requirements

- Primary touch points expected:
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/routes/internal.py`
- `apps/api/app/main.py` (only if runtime OpenAPI filtering needs correction)
- `apps/api/tests/test_auth_middleware.py`
- Additional callback-service/domain files only if needed for thin-route compliance.

### Testing Requirements

- Validate missing callback secret returns `401` for internal callback route.
- Validate incorrect callback secret returns `401` for internal callback route.
- Validate valid callback secret allows callback route to proceed to next processing step.
- Validate invalid-secret requests do not mutate in-memory store state/job counters.
- Verify `/openapi.json` remains aligned for callback path responses.
- Full verification gate: `make lint`, `make test`, `make check` in `apps/api`.

### Previous Story Intelligence

- Prior stories found contract drift quickly in runtime OpenAPI response filtering; keep callback route response set exact.
- No-leak behavior should remain consistent across protected resources; avoid introducing distinguishable unauthorized-vs-missing signals.
- Existing story files show success when route behavior is validated with both API tests and unit-level side-effect assertions.

### Git Intelligence Summary

- Recent work sequence:
- `e9479b3` Story 1.3 ownership + no-leak completion
- `0298c3a` Story 1.2 ownership boundaries
- `ecd2138` auth layer and route foundations
- Callback-secret work should build on current dependency wiring and avoid parallel auth mechanisms.

### Project Structure Notes

- No dedicated `architecture.md` artifact exists under `_bmad-output/planning-artifacts/`; derive implementation guardrails from OpenAPI, PRD, epics, project context, and completed story artifacts.
- Maintain existing `apps/api/app/{routes,services,repositories,schemas}` structure and current test organization.

### References

- `spec/api/openapi.yaml` (`/internal/jobs/{jobId}/status`, `internalCallbackSecret`, callback responses)
- `_bmad-output/planning-artifacts/epics.md` (Epic 1, Story 1.4)
- `_bmad-output/planning-artifacts/prd.md` (callback secret and write-endpoint security requirements)
- `_bmad-output/project-context.md` (Security Model, FSM/Idempotency invariants)
- `spec/acceptance/tasks_codex_v1.md` (Task 04 callback secret requirement)
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/routes/internal.py`
- `apps/api/tests/test_auth_middleware.py`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`

### Completion Notes List

- Implemented constant-time callback secret validation using `secrets.compare_digest` in route dependency.
- Added internal callback service handoff (`InternalCallbackService`) and invoked it from thin internal callback route.
- Added no-leak `404 RESOURCE_NOT_FOUND` behavior when callback targets a missing job under valid secret.
- Updated internal callback route OpenAPI `404` response model to `NoLeakNotFoundError`.
- Added/updated API tests for callback path behavior:
- valid secret + existing job returns `204`
- valid secret + missing job returns no-leak `404`
- invalid secret returns `401` with no mutation side effects
- internal callback path OpenAPI `404` schema reference uses `NoLeakNotFoundError`
- Verification completed in `apps/api`: `make lint`, `make test`, and `make check` all passed on 2026-02-23.
- ✅ Resolved review finding [HIGH]: Implemented callback domain processing semantics with FSM validation, idempotent replay (`200`), payload-mismatch conflict (`409`), and out-of-order conflict (`409`) in internal callback service.
- ✅ Resolved review finding [MEDIUM]: Updated callback request validation failures to return `409 VALIDATION_ERROR` instead of `401 UNAUTHORIZED`.
- ✅ Resolved review finding [MEDIUM]: Renamed unscoped repository job accessor to internal-only `get_job_for_internal_callback` and updated callback service usage.
- ✅ Resolved review finding [HIGH]: Added callback request optional contract fields (`actor_type`, `artifact_updates`, `failure_code`, `failure_message`, `failed_stage`) to `StatusCallbackRequest`.
- ✅ Resolved review finding [MEDIUM]: Internal callback route now declares contract-specific `409` conflict schemas (`FsmTransitionError`, `CallbackOrderingError`, `EventIdPayloadMismatchError`) as a oneOf.
- ✅ Resolved review finding [MEDIUM]: Callback ordering now rejects equal timestamps using strict monotonic guard (`occurred_at <= latest_applied_occurred_at`).
- Added callback flow guardrails in tests: replay behavior, payload mismatch conflict, out-of-order conflict, and applied-status mutation checks.
- Verification rerun completed in `apps/api` on 2026-02-26: `make lint`, `make test`, and `make check` all passed.

### File List

- `_bmad-output/implementation-artifacts/1-4-validate-internal-callback-secret.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/domain/job_fsm.py`
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/routes/internal.py`
- `apps/api/app/main.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/tests/test_auth_middleware.py`

### Change Log

- 2026-02-23: Implemented Story 1.4 callback-secret validation hardening, internal callback service handoff, missing-job no-leak `404`, and callback path test coverage; story moved to `review`.
- 2026-02-23: Senior code review completed with follow-up findings; story moved to `in-progress`.
- 2026-02-23: Resolved all code-review follow-ups (FSM/idempotency callback semantics, callback payload validation classification, internal-only job accessor) and moved story back to `review`.
- 2026-02-23: Second code review pass found additional contract-alignment gaps; story moved to `in-progress`.
- 2026-02-26: Completed second re-review follow-ups (callback request optional fields, contract-specific `409` schema modeling, strict timestamp monotonic ordering), reran `make lint`, `make test`, and `make check`, and moved story to `review`.
- 2026-02-26: Final contract-shape alignment for callback `409` OpenAPI (`oneOf`) completed; re-verified quality gates and moved story to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-02-23

### Outcome

- Changes Requested

### Summary

- Callback-secret gate hardening is in place and test coverage improved, but callback processing behavior for valid requests remains a no-op and does not yet satisfy Story 1.4 acceptance criteria end-to-end.
- Validation error handling currently conflates authentication and payload-shape failures on the callback route.

### Severity Breakdown

- High: 1
- Medium: 2
- Low: 0

### Action Items

- [x] [HIGH] Implement callback domain processing path for valid-secret requests so accepted callbacks do more than existence checks and align with intended FSM/idempotency behavior. [apps/api/app/services/internal_callbacks.py:12]
- [x] [MEDIUM] Correct callback request validation error classification to avoid returning `401 UNAUTHORIZED` for malformed payloads. [apps/api/app/main.py:70]
- [x] [MEDIUM] Limit unscoped `get_job` access surface to prevent bypass of owner-scoped repository patterns outside internal-only flows. [apps/api/app/repositories/memory.py:85]

### Re-Review (AI) - 2026-02-23

#### Outcome

- Changes Requested

#### Severity Breakdown

- High: 1
- Medium: 2
- Low: 0

#### Action Items

- [x] [HIGH] Add missing optional callback contract fields to `StatusCallbackRequest` (`actor_type`, `artifact_updates`, `failure_code`, `failure_message`, `failed_stage`). [apps/api/app/schemas/internal.py:10]
- [x] [MEDIUM] Replace generic `409 ErrorResponse` route declaration with contract-specific callback conflict schemas. [apps/api/app/routes/internal.py:23]
- [x] [MEDIUM] Reject equal timestamp callbacks as non-monotonic (`<= latest_applied_occurred_at`) per strict ordering policy. [apps/api/app/services/internal_callbacks.py:54]

### Final Re-Review (AI) - 2026-02-26

#### Outcome

- Approved

#### Summary

- Contract-aligned callback request schema fields are present.
- Callback `409` OpenAPI response now maps to explicit contract `oneOf` conflict schemas.
- Strict monotonic timestamp ordering is enforced, including equal timestamp rejection.
- Verification gates pass (`make lint`, `make test`, `make check`).
