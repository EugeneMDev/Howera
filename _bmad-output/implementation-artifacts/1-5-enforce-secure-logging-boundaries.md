# Story 1.5: Enforce Secure Logging Boundaries

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a security-conscious editor,
I want logs to exclude secrets and raw transcript payloads,
so that sensitive data is not leaked through observability systems.

## Acceptance Criteria

1. Given authenticated and callback flows with sensitive fields, when logs are emitted, then secrets and raw transcript content are omitted or redacted and correlation metadata remains available for debugging.
2. Given test scenarios covering auth and callback paths, when log output is inspected, then no forbidden sensitive values appear and the test suite fails on regression.

## Tasks / Subtasks

- [x] Implement secure logging boundaries for auth and callback flows (AC: 1)
- [x] Add structured logs for authenticated API flow outcomes without logging bearer tokens, callback secrets, transcript text, or prompt-like payloads.
- [x] Add structured logs for callback processing outcomes (accepted/replayed/rejected) that include safe correlation metadata (`correlation_id`, `event_id`, `job_id`) only.
- [x] Ensure callback/auth rejection paths do not include credential values in logs and preserve existing response contracts.
- [x] Keep routes thin and place logging behavior in dependency/service boundaries.
- [x] Add regression tests that fail on sensitive-log leakage (AC: 2)
- [x] Capture auth-flow logs in tests and assert correlation metadata is present while sensitive markers/tokens are absent.
- [x] Capture callback-flow logs in tests and assert transcript-like content and callback secret markers are absent.
- [x] Verify tests are deterministic and do not rely on external logging backends.
- [x] Verify quality and contract safety (AC: 1, 2)
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.
- [x] Confirm `/openapi.json` paths and response schemas remain unchanged for current implemented endpoints.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Sanitize and constrain user-controlled logging fields (`correlation_id`, `event_id`, `principal_id`) before emitting logs so arbitrary transcript/secrets cannot be injected into log lines. [apps/api/app/routes/dependencies.py:73]
- [x] [AI-Review][MEDIUM] Apply the same sanitization policy to callback service logs for `correlation_id`/`event_id` to prevent sensitive free-form payload fragments from being logged verbatim. [apps/api/app/services/internal_callbacks.py:31]
- [x] [AI-Review][MEDIUM] Add regression tests that prove transcript/secret-like content embedded in correlation/event identifiers is redacted or rejected from logs. [apps/api/tests/test_auth_middleware.py:431]

## Dev Notes

### Developer Context Section

- Story 1.1 established auth dependency boundaries.
- Story 1.4 established callback-secret gate and callback processing path with FSM/idempotency constraints.
- This story adds secure observability guardrails without changing endpoint contracts or introducing new API fields/status codes.

### Technical Requirements

- Do not log any raw credential values (`Authorization` bearer token, `X-Callback-Secret`, environment secret values).
- Do not log raw transcript or prompt-like payload content from callback artifacts/failure fields.
- Preserve useful debugging metadata by including correlation-safe identifiers (for example `correlation_id`, request path/method, and callback identifiers).
- Maintain no-leak API behavior and existing contract error shapes.

### Architecture Compliance

- `spec/` is source of truth and read-only.
- Contract-first: no endpoint/status/schema drift for this story.
- No business logic in route handlers; keep behavior in dependencies/services.
- Preserve callback idempotency/FSM handling and avoid side effects from logging changes.

### Library & Framework Requirements

- Use Python standard logging facilities.
- Use existing FastAPI dependency/service wiring; avoid adding external logging frameworks.
- Keep unit/API tests in existing `unittest` style under `apps/api/tests`.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/tests/test_auth_middleware.py`
- Add helper module only if needed for clear, reusable redaction/safe-log formatting.

### Testing Requirements

- Add regression tests for both authenticated and callback paths proving forbidden values do not appear in captured log output.
- Assert correlation metadata is still present in emitted logs for debugging.
- Keep existing story tests green and avoid contract-test regressions.
- Final verification gate: `make lint`, `make test`, `make check` in `apps/api`.

### Previous Story Intelligence

- Prior stories repeatedly surfaced OpenAPI drift risk; this story should avoid any route contract changes.
- Callback processing already has conflict/replay ordering behavior; logging additions must not alter those semantics.
- No-leak policy consistency is mandatory across protected flows.

### Git Intelligence Summary

- Epic 1 history shows incremental hardening in auth, ownership boundaries, and callback controls.
- Keep change set narrow and focused on secure logging + tests only.

### Project Structure Notes

- Current API codebase is intentionally minimal and service-oriented; prefer small targeted edits.
- Keep `_bmad-output` story artifacts aligned with sprint tracking states.

### References

- `spec/api/openapi.yaml` (`StatusCallbackRequest`, callback endpoint, correlation requirements)
- `spec/skills/80_security_baseline.yaml` (never log secrets/tokens/raw transcripts)
- `_bmad-output/planning-artifacts/epics.md` (Epic 1, Story 1.5)
- `_bmad-output/planning-artifacts/prd.md` (FR-032, security/privacy constraints)
- `_bmad-output/project-context.md` (security model and no-sensitive-logging baseline)
- `_bmad-output/implementation-artifacts/1-1-authenticate-api-requests-as-editor.md`
- `_bmad-output/implementation-artifacts/1-4-validate-internal-callback-secret.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`

### Completion Notes List

- Added safe auth/callback logging in dependency and callback service boundaries with correlation metadata and no credential/payload value logging.
- Added regression tests that capture logs and assert forbidden sensitive values are absent for auth and callback flows.
- Kept route/business contracts unchanged; existing OpenAPI contract test remained green.
- Verification completed in `apps/api`: `make lint`, `make test`, and `make check` all passed on 2026-02-26.
- ✅ Resolved review finding [HIGH]: user-controlled log identifiers are now emitted as deterministic hashed references rather than raw values.
- ✅ Resolved review finding [MEDIUM]: callback service logs now use the same safe identifier policy for `correlation_id` and `event_id`.
- ✅ Resolved review finding [MEDIUM]: added regression tests covering secret/transcript-like content inside identifier fields.

### File List

- `_bmad-output/implementation-artifacts/1-5-enforce-secure-logging-boundaries.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/core/logging_safety.py`
- `apps/api/tests/test_auth_middleware.py`

### Change Log

- 2026-02-26: Implemented Story 1.5 secure logging boundaries for auth and callback flows, added sensitive-log regression tests, ran full quality gates, and moved story to `review`.
- 2026-02-26: Senior code review completed with changes requested; follow-up security redaction items added and story moved to `in-progress`.
- 2026-02-26: Addressed all code-review follow-ups for identifier redaction, added coverage for identifier-based leakage, re-ran quality gates, and moved story back to `review`.
- 2026-02-26: Re-review completed with no remaining HIGH/MEDIUM issues; story moved to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-02-26

### Outcome

- Changes Requested

### Summary

- Core token/secret payload leakage controls are in place and existing tests pass.
- Remaining risk: user-controlled identifiers are logged verbatim, which still permits sensitive text injection into logs and weakens the secure-logging boundary.

### Severity Breakdown

- High: 1
- Medium: 2
- Low: 0

### Action Items

- [x] [HIGH] Sanitize and constrain user-controlled logging fields (`correlation_id`, `event_id`, `principal_id`) before emitting logs so arbitrary transcript/secrets cannot be injected into log lines. [apps/api/app/routes/dependencies.py:73]
- [x] [MEDIUM] Apply the same sanitization policy to callback service logs for `correlation_id`/`event_id` to prevent sensitive free-form payload fragments from being logged verbatim. [apps/api/app/services/internal_callbacks.py:31]
- [x] [MEDIUM] Add regression tests that prove transcript/secret-like content embedded in correlation/event identifiers is redacted or rejected from logs. [apps/api/tests/test_auth_middleware.py:431]

### Final Re-Review (AI) - 2026-02-26

#### Outcome

- Approved

#### Summary

- Identifier redaction is now enforced for auth and callback logs via deterministic safe tokens.
- Regression coverage includes identifier-injection cases and passes.
- Quality gates pass (`make lint`, `make test`, `make check`).
