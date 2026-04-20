# Story 4.5: Request Targeted Regeneration with Idempotency and Provenance

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want targeted regeneration with deduplication and provenance,
so that partial regeneration is reliable, traceable, and reproducible.

## Acceptance Criteria

1. Given regenerate request targets an owned instruction, when selection is submitted, then selection addressing is validated as either `block_id` or contract-defined text offsets and invalid selection returns contract-defined validation error.
2. Given regenerate request contains `client_request_id` (or dedupe key per policy), when duplicate request is received, then endpoint is idempotent and existing task reference is returned without creating duplicate work.
3. Given regenerate request is accepted, when task is created, then provenance is stored with `instruction_id`, `base_version`, `selection`, `requested_by`, `requested_at`, and where applicable `model_profile` and prompt template references.
4. Given regenerate task completes with `SUCCEEDED`, when output is persisted, then a new instruction version is created, validation is executed for that new version, and regenerate audit event is recorded.

## Tasks / Subtasks

- [x] Implement regenerate request domain model and persistence boundary (AC: 1, 2, 3, 4)
- [x] Add regenerate task persistence model/record with contract-aligned fields (`id`, `status`, provenance, timestamps, replay flag, optional outcome fields).
- [x] Add idempotency index for regenerate requests keyed by instruction scope + `client_request_id` and persist canonical request signature for replay safety.
- [x] Ensure regenerate task state model supports `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED` and outcome metadata (`instruction_version`, sanitized failure fields).
- [x] Implement contract-aligned request validation and route/service boundary (AC: 1, 2, 3)
- [x] Implement `POST /instructions/{instructionId}/regenerate` with authenticated owner-scoped behavior and thin-route/service-boundary pattern.
- [x] Enforce selection validation against contract one-of semantics (`block_id` xor `char_range`) and return contract-defined validation error on invalid payload.
- [x] Enforce `base_version` optimistic concurrency against current instruction version and return contract-defined `VERSION_CONFLICT` (`409`) with no mutation on stale base.
- [x] Enforce no-existence-leak policy for missing/non-owned instruction (`404 RESOURCE_NOT_FOUND`) with no side effects.
- [x] Implement idempotent regenerate request behavior (AC: 2)
- [x] On first accepted request, create task and return `202` with task payload.
- [x] On duplicate identical request, return `200` replay response with existing task payload and no duplicate task writes.
- [x] Preserve contract response set for regenerate endpoint (`200`, `202`, `400`, `404`, `409`) with no undocumented status regressions.
- [x] Persist provenance and completion linkage (AC: 3, 4)
- [x] Persist provenance fields for every accepted request: `instruction_id`, `base_version`, `selection`, `requested_by`, `requested_at`, optional `model_profile`, `prompt_template_id`, `prompt_params_ref`.
- [x] Ensure completion path for `SUCCEEDED` creates a new instruction version through shared instruction write boundary so structural validation metadata is populated (Story 4.4 continuity).
- [x] Persist resulting `instruction_version` reference on task and emit regenerate audit event with sanitized payload content only.
- [x] Ensure `FAILED` outcomes persist only sanitized failure fields (`failure_code`, safe `failure_message`, `failed_stage`) with no transcript/prompt/secret leakage.
- [x] Add AC-mapped tests + regression coverage (AC: 1, 2, 3, 4)
- [x] Add API tests for first regenerate request (`202`) and replay (`200`) returning same task reference without duplicate writes.
- [x] Add API tests for invalid selection (`400 VALIDATION_ERROR`) and stale base version (`409 VERSION_CONFLICT`) with no mutation.
- [x] Add API tests for no-leak ownership behavior (`404` for missing/non-owned instruction) and side-effect-free reject paths.
- [x] Add unit/service tests for idempotency signature handling, provenance persistence, and task status transitions.
- [x] Add completion-path tests proving `SUCCEEDED` creates new instruction version with validation metadata and audit event emission.
- [x] Add negative tests ensuring persisted failure fields/messages are sanitized and exclude transcript/prompt/secrets.
- [x] Re-verify `/openapi.json` includes contract-aligned regenerate endpoint schemas/response sets.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Preserve idempotent replay semantics after instruction version advances by checking existing `(instruction_id, client_request_id)` task replay before base-version conflict gating. [apps/api/app/services/instructions.py:91]
- [x] [AI-Review][MEDIUM] Include request `context` in regenerate payload signatures so duplicate `client_request_id` mismatches are detected and rejected. [apps/api/app/repositories/memory.py:769, apps/api/tests/test_instructions_ownership.py:383]
- [x] [AI-Review][MEDIUM] Align `/openapi.json` `RegenerateSelection` schema with contract `oneOf` (`block_id` xor `char_range`) to prevent schema drift. [apps/api/app/main.py:194, apps/api/tests/test_auth_middleware.py:258]

## Dev Notes

### Developer Context Section

- Epic 4 introduces transcript-driven authoring and instruction lifecycle quality guarantees; Story 4.5 adds targeted regenerate request intake, idempotency, and provenance as the entrypoint for async regenerate execution.
- Story 4.2/4.3 established instruction ownership, retrieval, and optimistic concurrency patterns; Story 4.4 established validation-on-write at shared instruction persistence boundaries.
- Story 4.5 should reuse those existing boundaries so regenerate-created instruction versions inherit existing validation metadata behavior automatically.

### Technical Requirements

- Endpoint in scope: `POST /instructions/{instructionId}/regenerate`.
- Contract behavior from OpenAPI:
  - `200`: idempotent replay; existing regenerate task returned.
  - `202`: regenerate task created.
  - `400`: invalid selection/payload (`VALIDATION_ERROR` semantics).
  - `404`: no-leak not found for missing/non-owned instruction.
  - `409`: base version conflict (`VersionConflictError`) with no mutation.
- Request contract (`RegenerateRequest`) requires:
  - `base_version` (integer, `minimum: 1`)
  - `selection` (`block_id` or `char_range`)
  - `client_request_id`
  - optional `context`, `model_profile`, `prompt_template_id`, `prompt_params_ref`
- Regenerate task/provenance contract fields:
  - task status enum: `PENDING | RUNNING | SUCCEEDED | FAILED`
  - provenance required: `instruction_id`, `base_version`, `selection`, `requested_by`, `requested_at`
  - success linkage: `instruction_version`
  - failure linkage: sanitized `failure_code`, `failure_message`, `failed_stage`
- Completion requirement continuity:
  - when regenerate result is persisted as new instruction version, validation-on-write from Story 4.4 must execute and persist validation metadata.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep business logic out of route handlers; place regenerate idempotency, provenance, and concurrency logic in service/repository boundaries.
- Preserve no-existence-leak behavior (`404`) for missing/non-owned instruction and task resources.
- Preserve provider isolation; no direct OpenAI SDK usage in domain/service logic.
- Preserve secure logging boundaries (no transcript, prompt content, or secrets in logs/audit payloads).
- Reuse FSM/idempotency/audit patterns already established for callback/retry flows where applicable.

### Library & Framework Requirements

- FastAPI + Pydantic contracts remain authoritative.
- Reuse existing typed error schema patterns (`VersionConflictError`, `NoLeakNotFoundError`, `Error`).
- Reuse shared instruction persistence boundary in repository/service layers to avoid duplicating validation behavior.
- No new external dependencies are expected unless explicitly justified and approved.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/instructions.py` (add regenerate POST handler)
- `apps/api/app/services/instructions.py` (add regenerate request service boundary and idempotency/concurrency logic)
- `apps/api/app/repositories/memory.py` (persist regenerate task records, dedupe index, provenance, completion linkage)
- `apps/api/app/schemas/instruction.py` (or dedicated regenerate schema module, if introduced) for request/task/provenance models
- `apps/api/app/main.py` (OpenAPI response-set shaping and validation remapping for contract-safe statuses, if needed)
- `apps/api/tests/test_instructions_ownership.py` (or targeted regenerate tests file) for API/unit coverage
- `apps/api/tests/test_auth_middleware.py` for OpenAPI contract assertions

### Testing Requirements

- Validate owned regenerate request success path returns `202` and contract task payload.
- Validate replay behavior returns `200` with same task reference and no duplicate writes/dispatches.
- Validate invalid selection and stale base-version conflict produce contract-compliant `400`/`409` with no mutation.
- Validate missing/non-owned instruction produces no-leak `404` with no side effects.
- Validate provenance fields persist exactly as contract requires for accepted requests.
- Validate completion success path creates new instruction version through shared validated persistence boundary.
- Validate failure fields are sanitized and do not leak transcript/prompt/secrets.
- Validate `/openapi.json` includes `/instructions/{instructionId}/regenerate` with `200/202/400/404/409` and schema refs.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 4.2 established instruction owner-scoping and no-leak `404` semantics for instruction resources; regenerate entrypoint must preserve those semantics.
- Story 4.3 established optimistic concurrency (`base_version`) and contract-safe `409 VERSION_CONFLICT` handling for instruction writes; regenerate request must enforce the same guardrail before task creation.
- Story 4.4 centralized structural validation on instruction-version persistence; regenerate success path should write new versions through that shared boundary to inherit validation metadata behavior.
- Prior review cycles in Epic 4 repeatedly surfaced contract drift risks around validation status handling and OpenAPI response schemas; keep explicit OpenAPI assertions for regenerate response sets and schema refs.

### Git Intelligence Summary

- Current backend patterns favor thin routes, service-bound business logic, deterministic in-memory repository behavior, and explicit no-side-effect assertions on reject paths.
- Existing retry/callback flows already model idempotency by request key + payload signature; regenerate request idempotency should reuse equivalent deterministic patterns.
- Existing test suite patterns use write counters and replay assertions; leverage these for regenerate dedupe and no-mutation reject-path coverage.

### Project Structure Notes

- No standalone architecture artifact is currently present in `_bmad-output/planning-artifacts/`; use `epics.md`, `prd.md`, OpenAPI, and recent Epic 4 implementation artifacts as guardrails.
- Keep Story 4.5 focused on regenerate request intake/idempotency/provenance and success-path version linkage; task polling endpoint behavior remains Story 4.6 scope.

### References

- `spec/api/openapi.yaml` (`RegenerateRequest`, `RegenerateSelection`, `RegenerateTask`, `RegenerateProvenance`, `/instructions/{instructionId}/regenerate`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.5)
- `_bmad-output/planning-artifacts/prd.md` (FR-020, FR-031, contract-first constraints)
- `spec/acceptance/tasks_codex_v1.md` (Task 10 regenerate model/idempotency/provenance intent)
- `_bmad-output/project-context.md` (idempotent async model, security boundaries, provider isolation)
- `_bmad-output/implementation-artifacts/4-2-retrieve-instruction-content-by-id.md`
- `_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md`
- `_bmad-output/implementation-artifacts/4-4-structural-validation-on-create-and-update-with-persisted-result.md`
- `apps/api/app/main.py`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/instruction.py`
- `apps/api/tests/test_instructions_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `spec/api/openapi.yaml`
- `spec/acceptance/tasks_codex_v1.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/4-2-retrieve-instruction-content-by-id.md`
- `_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md`
- `_bmad-output/implementation-artifacts/4-4-structural-validation-on-create-and-update-with-persisted-result.md`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/repositories/memory.py`

### Completion Notes List

- 2026-03-01: Created Story 4.5 artifact with targeted-regeneration request requirements, AC-mapped tasks, and implementation guardrails.
- 2026-03-01: Captured idempotency, provenance persistence, and contract-safe regenerate response semantics for `POST /instructions/{instructionId}/regenerate`.
- 2026-03-01: Incorporated continuity guardrails from Stories 4.2/4.3/4.4 (no-leak ownership, optimistic concurrency, validation-on-write).
- 2026-03-01: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-01: Implemented regenerate request schemas, route/service boundary, idempotent task persistence, provenance capture, and contract-safe validation/concurrency handling.
- 2026-03-01: Added regenerate completion/failure repository helpers to persist success instruction-version linkage, validation-on-write continuity, sanitized failure fields, and regenerate audit records.
- 2026-03-01: Added API and unit regression coverage for `200/202/400/404/409`, dedupe replay semantics, no-side-effect reject paths, payload-signature mismatch safety, and success/failure completion behavior.
- 2026-03-01: Verified quality gates in `apps/api` with `make lint`, `make test`, and `make check` (all passing).
- 2026-03-01: Completed senior code review, fixed replay-idempotency/version conflict ordering, added `context` to dedupe signatures, aligned `RegenerateSelection` OpenAPI to contract `oneOf`, reran quality gates, and moved story to `done`.

### File List

- `_bmad-output/implementation-artifacts/4-5-request-targeted-regeneration-with-idempotency-and-provenance.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/schemas/instruction.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_instructions_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Change Log

- 2026-03-01: Created Story 4.5 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-01: Started development and moved sprint status from `ready-for-dev` to `in-progress`.
- 2026-03-01: Implemented regenerate request intake with idempotency, provenance persistence, contract-safe validation behavior, and completion/failure persistence helpers.
- 2026-03-01: Added regenerate API/unit coverage and OpenAPI contract assertions; verified `make lint`, `make test`, and `make check`; moved story to `review`.
- 2026-03-01: Completed code-review follow-ups, re-verified quality gates, and moved story to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-03-01

### Outcome

- Approved

### Summary

- Core regenerate request behavior is now contract-aligned for idempotent replay, provenance persistence, and no-leak ownership handling.
- Replay semantics remain stable even after instruction version advances.
- OpenAPI now reflects contract `oneOf` selection shape and is covered by regression assertions.

### Severity Breakdown

- High: 1 (fixed)
- Medium: 2 (fixed)
- Low: 0
