# Story 4.2: Retrieve Instruction Content by ID

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to fetch instruction content by instruction ID,
so that I can review the current editable draft or a specific version.

## Acceptance Criteria

1. Given an authenticated editor requesting an owned instruction, when retrieval succeeds, then response includes required fields: `instruction_id`, `job_id`, `version`, `updated_at`, `validation_status`, and markdown content.
2. Given retrieval mode is latest by default, when no version is specified, then API returns latest instruction version.
3. Given retrieval mode requests a specific version, when version exists, then API returns that exact version payload and indicates version identity unambiguously.
4. Given resource is unauthorized or nonexistent, when retrieval is requested, then no-existence-leak policy is applied (`404`).

## Tasks / Subtasks

- [x] Implement `GET /instructions/{instructionId}` route and service boundary (AC: 1, 2, 3, 4)
- [x] Add instruction endpoint handler with authenticated owner-scoped behavior.
- [x] Keep route thin; retrieval, ownership checks, and version-selection logic must stay in service/repository boundaries.
- [x] Implement instruction contract schema support (AC: 1)
- [x] Add schema support for contract-aligned `Instruction` payload fields and types.
- [x] Ensure required fields are always present in `200` response: `instruction_id`, `job_id`, `version`, `markdown`, `updated_at`, `validation_status`.
- [x] Preserve backward-compat alias behavior for deprecated `id` field if present in contract shape.
- [x] Implement latest/specific-version retrieval semantics (AC: 2, 3)
- [x] Support optional query parameter `version` (`minimum=1`) and return latest version when omitted.
- [x] Return exact requested version when `version` is provided and exists.
- [x] Ensure version identity in response is unambiguous (`version` reflects persisted version returned).
- [x] Enforce no-existence-leak ownership semantics (AC: 4)
- [x] Return `404 RESOURCE_NOT_FOUND` for missing and non-owned instruction uniformly.
- [x] Ensure `404` reject paths do not mutate instruction/job/project state.
- [x] Preserve secure logging boundaries for instruction retrieval paths.
- [x] Add AC-mapped tests + contract assertions (AC: 1, 2, 3, 4)
- [x] Add API tests for latest retrieval success and versioned retrieval success.
- [x] Add API tests for non-owned and missing instruction no-leak `404`.
- [x] Add API tests for version query validation behavior (`minimum=1`) and no-side-effect reject paths.
- [x] Add unit tests for version-selection helper/service behavior and ownership no-leak semantics.
- [x] Update OpenAPI contract assertions for `/instructions/{instructionId}` `GET` response set (`200/404`) and parameter/schema refs.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Keep invalid `version` query failures within the endpoint contract response set (`200/404`) instead of returning undocumented FastAPI `422`; align runtime behavior and tests to contract-safe status handling. [apps/api/app/routes/instructions.py:25, apps/api/app/main.py:161, apps/api/tests/test_instructions_ownership.py:174]
- [x] [AI-Review][MEDIUM] Align `Instruction.id` schema metadata with contract (`deprecated: true`, alias description) while keeping it optional and non-null when present. [apps/api/app/schemas/instruction.py:22, spec/api/openapi.yaml]
- [x] [AI-Review][MEDIUM] Add explicit OpenAPI regression assertions for `Instruction.id` deprecated-alias metadata to prevent future contract drift. [apps/api/tests/test_auth_middleware.py:170, spec/api/openapi.yaml]

## Dev Notes

### Developer Context Section

- Epic 4 introduces instruction-domain read/write/versioning flows; Story 4.2 is the first instruction retrieval endpoint and establishes patterns reused by subsequent instruction stories.
- Story 4.1 finalized strict contract-first OpenAPI shaping and ownership/no-leak regression patterns; Story 4.2 should mirror those guardrails for instruction resources.
- Instruction retrieval is read-only and must not regress existing job/callback lifecycle invariants or secure logging boundaries.

### Technical Requirements

- Endpoint in scope: `GET /instructions/{instructionId}`.
- Contract behavior from OpenAPI:
  - `200` returns `Instruction`.
  - `404` returns `NoLeakNotFoundError` for missing/non-owned instruction.
- Query parameter:
  - `version` optional, integer, `minimum: 1`.
  - Omitted `version` returns latest instruction version.
  - Provided `version` returns exact version when available.
- `Instruction` contract required fields:
  - `instruction_id`, `job_id`, `version`, `markdown`, `updated_at`, `validation_status`.
- `validation_status` uses `ValidationStatus` enum (`PASS`/`FAIL`) and must remain contract-aligned.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Preserve no-existence-leak behavior for editor-facing resources (`404` for missing/non-owned).
- Keep business logic out of route handlers; use service/repository boundaries for retrieval and version selection.
- Preserve provider isolation and avoid direct SDK coupling in business logic.
- Preserve secure logging boundaries (no transcript/prompt/secrets leakage in logs).

### Library & Framework Requirements

- FastAPI routing and dependency wiring patterns should match existing `projects`/`jobs` endpoints.
- Pydantic models must be used for request/response contract shapes.
- Reuse existing `ApiError` + `NoLeakNotFoundError` response shaping patterns.
- No new external dependencies are expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes` (new instructions route module and router wiring)
- `apps/api/app/services` (instruction service boundary)
- `apps/api/app/repositories/memory.py` (instruction in-memory persistence + owner scoping/version selection)
- `apps/api/app/schemas` (instruction schemas and any contract enums/errors used)
- `apps/api/app/main.py` (OpenAPI response-set shaping, if needed)
- `apps/api/tests` (instruction API/service ownership and contract tests; openapi assertions)

### Testing Requirements

- Validate successful retrieval of latest instruction when `version` is omitted.
- Validate successful retrieval of exact instruction version when `version` query is provided.
- Validate required `Instruction` fields are present and contract-aligned.
- Validate non-owned/missing instruction returns no-leak `404 RESOURCE_NOT_FOUND`.
- Validate reject/validation paths do not mutate persisted state.
- Validate `/openapi.json` includes `/instructions/{instructionId}` `GET` with expected parameter and `200/404` response set.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 4.1 established strict OpenAPI assertions and response-code shaping through `apps/api/app/main.py` and `test_auth_middleware.py`; preserve this rigor for instruction endpoint contract checks.
- Story 4.1 added regression patterns asserting no-side-effect rejects via write counters; reuse this approach for instruction no-leak and validation paths.
- Story 3.x established consistent owner-scoped no-leak patterns in services/repositories; instruction retrieval should align to the same semantics.

### Git Intelligence Summary

- Current backend patterns favor:
  - thin routes + service-bound business logic
  - deterministic in-memory repositories for testability
  - explicit no-leak ownership checks with uniform `404` payloads
  - contract-focused OpenAPI tests in `test_auth_middleware.py`
- Story 4.2 should extend these patterns with minimal diff and no unrelated refactoring.

### Project Structure Notes

- Current codebase has no instruction route/service implementation yet; Story 4.2 introduces first instruction retrieval flow.
- Keep scope focused on retrieval-by-id + version-selection contract behavior only; defer update/concurrency flows to Story 4.3.

### References

- `spec/api/openapi.yaml` (`/instructions/{instructionId}` `GET`, `Instruction`, `ValidationStatus`, `NoLeakNotFoundError`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.2)
- `spec/acceptance/tasks_codex_v1.md` (Task 09)
- `_bmad-output/project-context.md` (ownership/security/contract invariants)
- `_bmad-output/implementation-artifacts/4-1-retrieve-transcript-segments-for-job.md` (recent implementation and test patterns)
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
- `_bmad-output/implementation-artifacts/4-1-retrieve-transcript-segments-for-job.md`
- `apps/api/app/routes`
- `apps/api/app/services`
- `apps/api/app/schemas`
- `apps/api/tests`

### Completion Notes List

- 2026-03-01: Created Story 4.2 artifact with contract-accurate instruction retrieval requirements, AC-mapped tasks, and implementation guardrails.
- 2026-03-01: Captured latest/specific-version retrieval semantics and strict no-leak ownership constraints for `GET /instructions/{instructionId}`.
- 2026-03-01: Marked Story 4.2 as `ready-for-dev` in sprint tracking.
- 2026-03-01: Implemented `GET /api/v1/instructions/{instructionId}` with owner-scoped no-leak `404`, latest-by-default retrieval, and explicit version retrieval via service/repository boundaries.
- 2026-03-01: Added `Instruction`/`ValidationStatus` schemas, in-memory instruction version storage, and OpenAPI shaping for contract-aligned instruction query schema.
- 2026-03-01: Added instruction API/unit tests and updated OpenAPI assertions for `/instructions/{instructionId}` (`200/404`, `version` minimum=1).
- 2026-03-01: Verification passed in `apps/api` with `make lint`, `make test`, and `make check`.
- 2026-03-01: Senior code review completed with changes requested; review follow-up tasks added and story moved to `in-progress`.
- 2026-03-01: Resolved all AI review follow-ups (contract-safe invalid `version` handling, `Instruction.id` deprecated alias metadata alignment, OpenAPI regression assertions), reran quality gates, and moved story to `done`.

### File List

- `_bmad-output/implementation-artifacts/4-2-retrieve-instruction-content-by-id.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/main.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/routes/__init__.py`
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/schemas/instruction.py`
- `apps/api/app/services/instructions.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_instructions_ownership.py`

### Change Log

- 2026-03-01: Created Story 4.2 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-01: Implemented instruction retrieval endpoint and supporting schema/service/repository wiring.
- 2026-03-01: Added instruction ownership/version-selection tests and OpenAPI contract assertions.
- 2026-03-01: Completed verification gates and advanced Story 4.2 to `review`.
- 2026-03-01: Senior code review completed with Changes Requested; status moved to `in-progress` and AI follow-ups added.
- 2026-03-01: Applied all code-review fixes, reran quality gates, and moved story to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-03-01

### Outcome

- Changes Requested

### Summary

- Core instruction retrieval behavior is implemented and AC coverage is broadly in place.
- Contract conformance gaps remain around invalid-query runtime status handling and schema metadata parity for deprecated alias fields.

### Severity Breakdown

- High: 1
- Medium: 2
- Low: 0

### Action Items

- [x] [HIGH] Invalid `version` queries currently return FastAPI `422`, which is outside this endpoint's documented contract response set (`200/404`).
  - Evidence: query validation is enforced at route parameter level via `Query(ge=1)`, while request-validation remapping does not include this route and tests assert `422`.
  - References: `apps/api/app/routes/instructions.py:25`, `apps/api/app/main.py:161`, `apps/api/tests/test_instructions_ownership.py:174`.
- [x] [MEDIUM] `Instruction.id` OpenAPI metadata does not match contract requirements for deprecated alias semantics.
  - Evidence: schema field is emitted as nullable without `deprecated: true` and without contract alias description.
  - References: `apps/api/app/schemas/instruction.py:22`, `spec/api/openapi.yaml`.
- [x] [MEDIUM] OpenAPI tests do not assert deprecated alias metadata for `Instruction.id`, allowing this contract drift to pass undetected.
  - Evidence: current assertions verify path response refs and `version` parameter constraints but not `Instruction.id` metadata.
  - References: `apps/api/tests/test_auth_middleware.py:170`, `spec/api/openapi.yaml`.

### Final Re-Review (AI) - 2026-03-01

#### Outcome

- Approved

#### Summary

- Invalid instruction `version` query validation is now mapped to contract-safe no-leak `404` handling (no undocumented `422` for this endpoint).
- `Instruction.id` OpenAPI now carries deprecated alias metadata required by contract (`type: string`, `deprecated: true`, alias description).
- OpenAPI regression tests now assert the `Instruction.id` deprecated alias metadata to prevent future drift.
- Verification passed: `make lint`, `make test`, `make check` in `apps/api`.
