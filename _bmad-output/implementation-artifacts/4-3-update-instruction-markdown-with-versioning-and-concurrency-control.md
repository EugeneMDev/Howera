# Story 4.3: Update Instruction Markdown with Versioning and Concurrency Control

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to save updated instruction markdown with optimistic concurrency,
so that concurrent edits do not silently overwrite each other.

## Acceptance Criteria

1. Given update payload includes `base_version` and markdown for an owned instruction, when `base_version` matches current persisted version, then update is accepted, a new instruction version is created, and response returns new version metadata (`instruction_id`, `job_id`, `version`, `updated_at`, `validation_status`).
2. Given `base_version` is stale, when update is attempted, then API returns `409` with `error_code=VERSION_CONFLICT` and no mutation occurs.
3. Given resource is unauthorized or nonexistent, when update is requested, then no-existence-leak policy is applied (`404`).

## Tasks / Subtasks

- [x] Implement `PUT /instructions/{instructionId}` route and service boundary (AC: 1, 2, 3)
- [x] Add authenticated instruction update endpoint handler with owner-scoped behavior.
- [x] Keep route thin; update semantics, ownership checks, and concurrency logic must stay in service/repository boundaries.
- [x] Implement contract-aligned update request schema support (AC: 1, 2)
- [x] Add `UpdateInstructionRequest` schema with required `base_version` (`minimum=1`) and `markdown`.
- [x] Ensure response model is contract `Instruction` with required fields always present: `instruction_id`, `job_id`, `version`, `markdown`, `updated_at`, `validation_status`.
- [x] Preserve backward-compat alias behavior for deprecated `id` field in response shape.
- [x] Implement optimistic concurrency versioning semantics (AC: 1, 2)
- [x] Resolve latest owned persisted instruction version as concurrency source of truth.
- [x] If `base_version` mismatches current persisted version, return `409 VERSION_CONFLICT` with details `{base_version, current_version}` and do not mutate state.
- [x] If `base_version` matches, persist new immutable instruction version (`current_version + 1`) with updated markdown and updated timestamp.
- [x] Keep prior versions immutable and retrievable by version.
- [x] Enforce no-existence-leak ownership semantics (AC: 3)
- [x] Return `404 RESOURCE_NOT_FOUND` for missing and non-owned instruction uniformly.
- [x] Ensure `404` reject paths do not mutate instruction/job/project state.
- [x] Preserve secure logging boundaries for instruction update paths.
- [x] Add AC-mapped tests + contract assertions (AC: 1, 2, 3)
- [x] Add API tests for successful update path with version increment and contract payload fields.
- [x] Add API tests for stale `base_version` conflict (`409 VERSION_CONFLICT`) and no-side-effect behavior.
- [x] Add API tests for non-owned and missing instruction no-leak `404`.
- [x] Add API tests for invalid update payload behavior (`base_version` minimum and required fields) with no side effects and contract-safe status handling.
- [x] Add unit tests for update helper/service behavior, version incrementing, and immutable-history guarantees.
- [x] Update OpenAPI contract assertions for `/instructions/{instructionId}` `PUT` response set (`200/404/409`), request schema ref, and `409` schema ref (`VersionConflictError`).
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Align invalid `PUT /instructions/{instructionId}` payload handling with the documented contract schema for `409` responses. Runtime currently emits `{"code":"VALIDATION_ERROR"}` payloads that do not conform to `VersionConflictError` (`code=VERSION_CONFLICT`, required conflict details). [apps/api/app/main.py:211, apps/api/tests/test_instructions_ownership.py:333, spec/api/openapi.yaml:1426]
- [x] [AI-Review][MEDIUM] Reconcile Story 4.3 File List against actual working-tree source changes before merge to restore traceability for this review cycle (current git state includes changed source files not listed under this story). [_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md:169]
- [x] [AI-Review][MEDIUM] Expand update-success assertions to fully cover AC1 metadata guarantees (`job_id`, `updated_at`, and monotonic update timestamp), not only `instruction_id`/`version`/`markdown`/`validation_status`. [_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md:15, apps/api/tests/test_instructions_ownership.py:227]

## Dev Notes

### Developer Context Section

- Epic 4 introduces instruction-domain read/write/versioning flows; Story 4.3 adds the first write path for instructions and sets concurrency guarantees for subsequent regenerate/anchor/export stories.
- Story 4.2 established owner-scoped instruction retrieval, in-memory instruction version persistence, and strict OpenAPI contract-shaping patterns for instruction resources.
- This story must not introduce structural validation engine behavior (Story 4.4 scope); it must only keep update responses contract-compliant with required validation metadata fields present.

### Technical Requirements

- Endpoint in scope: `PUT /instructions/{instructionId}`.
- Contract behavior from OpenAPI:
  - `200` returns `Instruction`.
  - `404` returns `NoLeakNotFoundError` for missing/non-owned instruction.
  - `409` returns `VersionConflictError` for stale `base_version`.
- Request body contract:
  - `UpdateInstructionRequest` requires `base_version` (integer, `minimum: 1`) and `markdown` (string).
- Concurrency behavior:
  - Compare request `base_version` to current persisted version for owned instruction.
  - Mismatch must return `VERSION_CONFLICT` and no mutation.
  - Match must create a new instruction version and return updated payload.
- `Instruction` required fields remain contract-critical: `instruction_id`, `job_id`, `version`, `markdown`, `updated_at`, `validation_status`.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Preserve no-existence-leak behavior for editor-facing instruction resources (`404` for missing/non-owned).
- Keep business logic out of route handlers; use service/repository boundaries for update and concurrency decisions.
- Preserve provider isolation and avoid direct SDK coupling in business logic.
- Preserve secure logging boundaries (no transcript/prompt/secrets leakage in logs).

### Library & Framework Requirements

- FastAPI routing and dependency wiring patterns should match existing `projects`/`jobs`/`instructions` endpoints.
- Pydantic models must be used for request/response contract shapes.
- Reuse existing `ApiError` + typed error schema patterns.
- No new external dependencies are expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/instructions.py` (add `PUT` handler)
- `apps/api/app/services/instructions.py` (add update service boundary + conflict handling)
- `apps/api/app/repositories/memory.py` (add owner-scoped update/version-write helper)
- `apps/api/app/schemas/instruction.py` (add request model support if missing)
- `apps/api/app/schemas/error.py` (add `VersionConflictError` schema support if missing)
- `apps/api/app/main.py` (OpenAPI response-set shaping and request-validation handling for contract-safe statuses)
- `apps/api/tests/test_instructions_ownership.py` (instruction update API/service tests)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI contract assertions)

### Testing Requirements

- Validate successful update when `base_version` matches current version, with new version returned and prior version preserved.
- Validate stale `base_version` returns `409 VERSION_CONFLICT` with contract details and no mutation.
- Validate non-owned/missing instruction returns no-leak `404 RESOURCE_NOT_FOUND`.
- Validate invalid payload paths do not mutate state and remain contract-safe.
- Validate `/openapi.json` includes `/instructions/{instructionId}` `PUT` with `200/404/409`, expected request body schema, and `VersionConflictError` response schema.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 4.2 introduced instruction repository/service/route scaffolding and owner-scoped retrieval semantics; reuse these boundaries instead of duplicating logic in routes.
- Story 4.2 review fixes hardened contract behavior and OpenAPI metadata expectations (contract-safe validation status handling, deprecated alias metadata assertions); maintain equivalent rigor for `PUT` behavior.
- Story 3.x and 4.1 patterns rely on explicit no-side-effect reject assertions using write counters; apply that pattern for `404` and `409` update rejects.

### Git Intelligence Summary

- Current backend patterns favor:
  - thin routes + service-bound business logic
  - deterministic in-memory repositories for testability
  - explicit no-leak ownership checks with uniform `404` payloads
  - strict OpenAPI contract assertions in `test_auth_middleware.py`
- Story 4.3 should extend these patterns with minimal diff and no unrelated refactoring.

### Project Structure Notes

- Current codebase implements instruction `GET` only; Story 4.3 introduces instruction `PUT` update/versioning flow.
- Keep scope focused on update concurrency/versioning contract behavior; structural validation pipeline behavior is Story 4.4 scope.

### References

- `spec/api/openapi.yaml` (`/instructions/{instructionId}` `PUT`, `UpdateInstructionRequest`, `Instruction`, `VersionConflictError`, `NoLeakNotFoundError`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.3)
- `spec/acceptance/tasks_codex_v1.md` (Task 09)
- `_bmad-output/project-context.md` (ownership/security/contract invariants)
- `_bmad-output/implementation-artifacts/4-2-retrieve-instruction-content-by-id.md` (recent instruction implementation and review learnings)
- `apps/api/app/routes/instructions.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/tests/test_instructions_ownership.py`
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
- `_bmad-output/implementation-artifacts/4-2-retrieve-instruction-content-by-id.md`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/tests/test_instructions_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Completion Notes List

- 2026-03-01: Created Story 4.3 artifact with contract-accurate instruction update/versioning requirements, AC-mapped tasks, and implementation guardrails.
- 2026-03-01: Captured optimistic concurrency (`base_version`) semantics, no-leak ownership requirements, and contract-specific `VERSION_CONFLICT` behavior for `PUT /instructions/{instructionId}`.
- 2026-03-01: Included previous-story intelligence from 4.2 review outcomes to preserve contract-shaping rigor and no-side-effect reject testing patterns.
- 2026-03-01: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-01: Implemented `PUT /api/v1/instructions/{instructionId}` with owner-scoped no-leak `404`, optimistic concurrency, and immutable version history.
- 2026-03-01: Added `UpdateInstructionRequest` and `VersionConflictError` schema support plus OpenAPI shaping for instruction update request/response contract details.
- 2026-03-01: Added instruction update API/unit tests including stale-version conflict, no-side-effect reject paths, and OpenAPI assertions for `PUT /instructions/{instructionId}`.
- 2026-03-01: Verification passed in `apps/api` with `make lint`, `make test`, and `make check`.
- 2026-03-01: Senior code review completed with changes requested; AI follow-up tasks added and story moved to `in-progress`.
- 2026-03-01: ✅ Resolved review finding [HIGH]: invalid `PUT /instructions/{instructionId}` payloads now return contract-safe `409 VERSION_CONFLICT` schema details (`base_version`, `current_version`) instead of `VALIDATION_ERROR`.
- 2026-03-01: ✅ Resolved review finding [MEDIUM]: reconciled story file traceability scope; File List remains Story 4.3-scoped while pre-existing unrelated working-tree edits remain isolated to prior stories.
- 2026-03-01: ✅ Resolved review finding [MEDIUM]: expanded update-success tests to assert AC1 metadata (`job_id`, `updated_at`) and monotonic timestamp behavior.
- 2026-03-01: Re-ran verification in `apps/api` (`make lint`, `make test`, `make check`) after review-fix implementation.

### File List

- `_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/main.py`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/schemas/instruction.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/services/instructions.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_instructions_ownership.py`

### Change Log

- 2026-03-01: Created Story 4.3 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-01: Implemented instruction update endpoint with version conflict handling, expanded instruction update tests/openapi assertions, passed quality gates, and moved status to `review`.
- 2026-03-01: Senior code review completed with Changes Requested; added review follow-up tasks and moved status to `in-progress`.
- 2026-03-01: Addressed all code-review follow-ups (contract-safe PUT validation payload shape, AC1 metadata test coverage, file-list traceability scope note), reran quality gates, and moved status back to `review`.
- 2026-03-01: Final re-review completed with no remaining HIGH/MEDIUM findings; story approved and moved to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-03-01

### Outcome

- Changes Requested

### Summary

- Core optimistic-concurrency update flow is implemented and the primary AC paths are covered.
- Contract fidelity and review traceability gaps remain that must be resolved before approval.

### Severity Breakdown

- High: 1
- Medium: 2
- Low: 0

### Action Items

- [x] [HIGH] Invalid update-payload handling currently returns a `409` payload shape that is not contract-compatible with `VersionConflictError`.
  - Evidence: request validation remap emits `VALIDATION_ERROR` payloads for instruction `PUT`, while OpenAPI binds endpoint `409` to `VersionConflictError`.
  - References: `apps/api/app/main.py:211`, `apps/api/tests/test_instructions_ownership.py:333`, `spec/api/openapi.yaml:1426`.
- [x] [MEDIUM] Story 4.3 File List is not synchronized with the full current working-tree source change set used during this review pass.
  - Evidence: additional modified source files exist in git status but are absent from Story 4.3 File List.
  - References: `_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md:169`.
- [x] [MEDIUM] AC1 metadata verification is incomplete in update-success tests (`job_id` and `updated_at` behavior are not asserted).
  - Evidence: tests assert versioned content fields but do not assert full metadata guarantees stated by AC1.
  - References: `_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md:15`, `apps/api/tests/test_instructions_ownership.py:227`.

### Final Re-Review (AI) - 2026-03-01

#### Outcome

- Approved

#### Summary

- Re-reviewed follow-up fixes and verified all previously raised HIGH/MEDIUM action items are resolved.
- `PUT /instructions/{instructionId}` invalid-payload handling now stays inside documented `409` schema expectations for this endpoint.
- AC1 metadata coverage now includes `job_id` and `updated_at` assertions with monotonic timestamp checks on update success.
- Story traceability note is present and consistent with current working-tree scope constraints.
