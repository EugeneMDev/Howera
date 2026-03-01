# Story 4.4: Structural Validation on Create and Update with Persisted Result

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want structural validation to run on instruction create and update,
so that instruction quality status is explicit and traceable.

## Acceptance Criteria

1. Given an instruction version is created (generation, regeneration, or save), when persistence completes, then structural validation runs automatically on create and on update.
2. Given validation completes, when result is stored, then persisted validation fields include `validation_status` (`PASS` or `FAIL`), `errors[]`, `validated_at`, and `validator_version`.
3. Given validation fails, when errors are recorded, then `errors[]` contains schema and structure diagnostics only and excludes transcript, prompt content, and secrets from persisted errors and logs.

## Tasks / Subtasks

- [ ] Implement structural-validation domain boundary and normalized result model (AC: 1, 2, 3)
- [ ] Add a dedicated instruction validation helper/module that evaluates markdown structure and returns normalized diagnostics.
- [ ] Keep validation engine deterministic and side-effect free; avoid logging raw markdown or prompt/transcript-like content.
- [ ] Define validator versioning strategy (static `validator_version` identifier) for persisted traceability.
- [ ] Enforce validation on every instruction version write path (create + update) (AC: 1, 2)
- [ ] Apply validation automatically at the shared instruction-version persistence boundary so generation/regeneration/save flows inherit the same behavior.
- [ ] Ensure update flows do not bypass validation and always persist fresh validation metadata on newly created versions.
- [ ] Preserve immutable prior versions and ensure new versions carry their own validation snapshot.
- [ ] Persist contract-aligned validation metadata and sanitized diagnostics (AC: 2, 3)
- [ ] Persist `validation_status`, `validation_errors` (`errors[]` equivalent), `validated_at`, and `validator_version` for each new instruction version.
- [ ] Record only structural/schema diagnostics (`code`, safe `message`, optional `path`) and exclude transcript, prompt content, secrets, and free-form sensitive payloads.
- [ ] Preserve no-existence-leak behavior and existing contract-safe status handling for instruction reads/updates.
- [ ] Add AC-mapped tests + regression coverage (AC: 1, 2, 3)
- [ ] Add unit tests for validator pass/fail outcomes, deterministic diagnostics, and sanitization constraints.
- [ ] Add API/service tests proving update-created versions persist expected validation fields and preserve prior version metadata immutably.
- [ ] Add create-path tests at the shared persistence boundary to verify validation executes for non-update instruction version creation flows.
- [ ] Add negative tests ensuring sensitive strings are not stored in validation diagnostics or logs.
- [ ] Re-verify `/openapi.json` instruction schemas remain contract-aligned for validation fields and enums.
- [ ] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Epic 4 introduces instruction-domain authoring and quality controls; Story 4.4 adds structural validation guarantees that underpin future regenerate (4.5) and task-polling (4.6) behaviors.
- Story 4.2/4.3 established instruction retrieval/update boundaries, no-leak ownership semantics, and strict OpenAPI shaping; Story 4.4 must preserve those invariants.
- Validation in this story is structural/schema-focused only; it is not a content-quality or prompt-evaluation engine.

### Technical Requirements

- Validation must run whenever a new instruction version is persisted, including:
  - create path (generation/regeneration/save semantics)
  - update path (`PUT /instructions/{instructionId}`)
- Persisted validation metadata must include:
  - `validation_status` (`PASS` | `FAIL`)
  - diagnostics collection (`errors[]` in story language; `validation_errors` in current contract schema)
  - `validated_at`
  - `validator_version`
- Diagnostics must be safe and bounded:
  - include structural/schema `code`, safe `message`, optional `path`
  - exclude transcript fragments, prompt content, and secrets
- Do not add or change endpoints/status codes outside the existing OpenAPI contract.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep business logic out of routes; place validation and persistence rules in service/domain/repository boundaries.
- Preserve no-existence-leak behavior for instruction resources (`404` for missing/non-owned).
- Preserve provider isolation; no direct SDK coupling in business/domain logic.
- Preserve secure logging boundaries (no secrets/raw transcript/prompt leakage).

### Library & Framework Requirements

- FastAPI + Pydantic contracts remain authoritative.
- Reuse existing instruction schemas (`Instruction`, `ValidationStatus`, `ValidationIssue`) and typed error patterns.
- No new external dependencies are expected unless explicitly justified and approved.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/domain/` (new or extended structural validation helper/model)
- `apps/api/app/repositories/memory.py` (shared instruction-version write boundary with validation persistence)
- `apps/api/app/services/instructions.py` (ensure update flow consistently uses validated write path)
- `apps/api/app/schemas/instruction.py` (only if contract-aligned validation schema refinements are required)
- `apps/api/app/main.py` (only if OpenAPI shaping needs alignment fixes)
- `apps/api/tests/test_instructions_ownership.py` (instruction validation behavior tests)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI contract assertions if schema behavior changes)

### Testing Requirements

- Validate validation runs on update-created instruction versions and persists required metadata.
- Validate shared create-path version writes also run validation automatically.
- Validate `PASS`/`FAIL` outcomes and deterministic diagnostics behavior.
- Validate diagnostics/logging sanitization boundaries (no transcript/prompt/secret leakage).
- Validate no regressions for instruction no-leak ownership and optimistic-concurrency behavior.
- Validate `/openapi.json` still exposes contract-aligned instruction schema fields and response sets.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 4.2 hardened instruction read contract behavior, including validation/query contract safety and deprecated alias metadata checks.
- Story 4.3 introduced update versioning/concurrency and fixed contract-safe `409` behavior; do not regress these semantics while adding validation.
- Prior review cycles showed contract drift risks around validation error handling and schema refs; keep explicit OpenAPI assertions where applicable.

### Git Intelligence Summary

- Current backend patterns favor thin routes, service-bound business logic, and deterministic in-memory repositories.
- Instruction version history is immutable-by-version and already test-driven; Story 4.4 should extend this with minimal diff and no unrelated refactor.
- Existing test suite uses write counters and no-side-effect assertions for reject paths; reuse these patterns for validation-related regressions.

### Project Structure Notes

- No standalone architecture artifact is present in `_bmad-output/planning-artifacts/`; use `epics.md`, `prd.md`, OpenAPI contract, and recent story artifacts as implementation guardrails.
- Keep scope focused on structural validation persistence and safety; targeted regenerate task modeling remains Story 4.5 scope.

### References

- `spec/api/openapi.yaml` (`Instruction`, `ValidationStatus`, `ValidationIssue`, `/instructions/{instructionId}` `PUT`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.4)
- `_bmad-output/planning-artifacts/prd.md` (FR-045 and contract-first constraints)
- `spec/acceptance/tasks_codex_v1.md` (Task 09 instruction read/write + validation persistence intent)
- `_bmad-output/project-context.md` (architectural invariants and security constraints)
- `_bmad-output/implementation-artifacts/4-2-retrieve-instruction-content-by-id.md`
- `_bmad-output/implementation-artifacts/4-3-update-instruction-markdown-with-versioning-and-concurrency-control.md`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/instructions.py`
- `apps/api/tests/test_instructions_ownership.py`

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
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/instructions.py`
- `apps/api/tests/test_instructions_ownership.py`

### Completion Notes List

- 2026-03-01: Created Story 4.4 artifact with structural-validation requirements for instruction create/update flows and AC-mapped implementation tasks.
- 2026-03-01: Captured validation persistence requirements (`validation_status`, diagnostics, `validated_at`, `validator_version`) with explicit sanitization guardrails.
- 2026-03-01: Included previous-story intelligence from 4.2/4.3 to preserve contract-safe behavior and no-leak semantics.
- 2026-03-01: Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/4-4-structural-validation-on-create-and-update-with-persisted-result.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-01: Created Story 4.4 artifact and moved sprint status from `backlog` to `ready-for-dev`.
