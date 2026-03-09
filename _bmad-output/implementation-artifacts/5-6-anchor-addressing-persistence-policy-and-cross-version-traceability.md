# Story 5.6: Anchor Addressing, Persistence Policy, and Cross-Version Traceability

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want anchors linked to instruction blocks to remain stable across version updates,
so that screenshot references stay predictable through edits.

## Acceptance Criteria

1. Given anchor create request, when addressing is validated, then supported addressing types are `block_id` (primary) and `char_range` (fallback), and stored anchor includes addressing type, value, and strategy metadata.
2. Given instruction version changes, when v1 anchor resolution policy runs, then each anchor is classified as `retain`, `remap`, or `unresolved`, and trace metadata is stored linking source version to target version resolution result.
3. Given anchor and asset mutation operations (`extract`, `replace`, `delete`, `upload`, `annotate`), when persistence occurs, then anchor and asset updates are transactional and ownership-scoped, and no cross-owner mutation is possible.
4. Given export references anchored visuals, when export payload is built, then export binds exact anchor and asset versions (not floating latest), and provenance records those exact references.

## Tasks / Subtasks

- [x] Implement anchor lifecycle contract endpoints and service boundaries (AC: 1, 2)
- [x] Add `POST /instructions/{instructionId}/anchors` with `ScreenshotAnchorCreateRequest` contract handling and owner/no-leak behavior (`201/404`).
- [x] Add `GET /instructions/{instructionId}/anchors` with query filtering for `instruction_version_id` and `include_deleted_assets` per contract.
- [x] Add `GET /anchors/{anchorId}` with optional `target_instruction_version_id` support and no-leak `404` semantics.
- [x] Implement addressing validation and persistence metadata (AC: 1)
- [x] Enforce `address_type` enum constraints (`block_id`, `char_range`) with required field/value consistency at write time.
- [x] Persist addressing metadata (`address_type`, address value, `strategy`) with deterministic shape in stored anchors.
- [x] Validate instruction version context for anchor creation to avoid orphan/mismatched records.
- [x] Implement v1 cross-version resolution policy and trace persistence (AC: 2)
- [x] Add anchor resolution classification (`retain`, `remap`, `unresolved`) from source instruction version to target version.
- [x] Persist or deterministically compute `resolution.trace` linking source/target version and resolution method evidence.
- [x] Ensure retrieval/listing returns contract-aligned `resolution` structure when target version context is provided.
- [x] Preserve transactional ownership-scoped mutation invariants (AC: 3)
- [x] Ensure anchor state and linked asset references remain owner-scoped across create/list/get and downstream mutation calls.
- [x] Keep anchor/asset mutations logically atomic so failed updates do not persist partial chain mutations.
- [x] Add regression coverage to confirm no cross-owner anchor or asset mutation side effects.
- [x] Preserve exact anchor/asset reference stability for downstream export provenance (AC: 4)
- [x] Ensure anchor retrieval surfaces exact `active_asset_id` and stable version-linked asset history needed for deterministic export binding.
- [x] Avoid floating-latest ambiguity by keeping explicit instruction-version + anchor linkage in anchor records.
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2, 3, 4)
- [x] Add API tests for create/list/get happy paths and contract response sets.
- [x] Add API tests for addressing validation errors and no-leak `404` behavior.
- [x] Add API/unit tests for `retain/remap/unresolved` resolution behavior and trace payload structure.
- [x] Add tests for owner scoping + transactional no-partial-state guarantees on failed/mismatched operations.
- [x] Re-verify `/openapi.json` includes `/instructions/{instructionId}/anchors` and `/anchors/{anchorId}` with expected schemas and response codes.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 5.1 through 5.5 implemented screenshot extraction/replacement/delete/upload/attach/annotate lifecycle and deterministic asset versioning patterns.
- Story 5.6 completes Epic 5 anchor-lifecycle scope by implementing anchor create/list/get and cross-version traceability policy (Task 12 acceptance scope).
- Contract-first boundaries remain strict: no endpoint/status/schema additions outside `spec/api/openapi.yaml`.

### Technical Requirements

- Endpoints in scope:
- `POST /instructions/{instructionId}/anchors`
- `GET /instructions/{instructionId}/anchors`
- `GET /anchors/{anchorId}`
- Contract behavior from OpenAPI:
- Create anchor: `201` (`ScreenshotAnchor`), `404` (no-leak).
- List anchors: `200` (array of `ScreenshotAnchor`), `404` (no-leak).
- Get anchor: `200` (`ScreenshotAnchor`), `404` (no-leak).
- Query/shape requirements:
- List supports optional `instruction_version_id` and `include_deleted_assets` (default `false`).
- Get supports optional `target_instruction_version_id` for resolution projection.
- Schema requirements:
- `ScreenshotAnchorCreateRequest` requires `instruction_version_id` and `addressing`.
- `AnchorAddress` requires `address_type` enum `block_id|char_range` with `block_id`, `char_range`, `strategy`.
- `AnchorResolution` requires `source_instruction_version_id`, `target_instruction_version_id`, `resolution_state` enum `retain|remap|unresolved`.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep route handlers thin; enforce ownership, addressing validation, resolution policy, and transactional persistence in service/repository layers.
- Preserve no-existence-leak policy (`404`) for unauthorized/missing instruction or anchor context.
- Maintain artifact discipline and deterministic version linkage from prior screenshot lifecycle stories.
- Ensure anchor/asset linkage semantics remain deterministic for export provenance consumers.

### Library & Framework Requirements

- FastAPI + Pydantic remain contract authority for request/response and query handling.
- Reuse existing owner-scoped repository patterns and deterministic version-chain behavior from Stories 5.1-5.5.
- Reuse OpenAPI shaping and contract assertions in `app/main.py` and `test_auth_middleware.py`.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/schemas/job.py` (anchor create request and anchor resolution schema alignment as needed)
- `apps/api/app/routes/jobs.py` and/or `apps/api/app/routes/instructions.py` (anchor create/list/get handlers)
- `apps/api/app/services/jobs.py` and/or `apps/api/app/services/instructions.py` (owner-scoped anchor lifecycle orchestration)
- `apps/api/app/repositories/memory.py` (anchor persistence, retrieval filters, cross-version resolution/trace logic)
- `apps/api/app/main.py` (OpenAPI response-code allowlist, schema shaping, validation-path mapping)
- `apps/api/tests/test_jobs_ownership.py` and/or `apps/api/tests/test_instructions_ownership.py` (API + unit coverage)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI path/schema assertions)

### Testing Requirements

- Validate anchor creation returns `201` with contract-required `ScreenshotAnchor` structure.
- Validate addressing-type/value consistency enforcement for `block_id` and `char_range`.
- Validate list/get behavior for owner-only reads and no-leak `404` for cross-owner/missing resources.
- Validate list filter behavior (`instruction_version_id`, `include_deleted_assets`) and deterministic ordering.
- Validate get-anchor resolution behavior for target instruction versions (`retain/remap/unresolved`) with trace metadata.
- Validate transactional/ownership guarantees across anchor and linked asset mutation contexts.
- Validate `/openapi.json` contract alignment for anchor lifecycle endpoints and schema refs.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 5.5 delivered deterministic annotation operation hashing (`ops_hash`), replay-safe render linkage, and render-failure no-mutation guarantees.
- Story 5.4 delivered signed upload and attach semantics with explicit version-chain updates.
- Story 5.3 delivered soft-delete fallback traversal across `previous_asset_id`.
- Story 5.6 should build directly on these deterministic/versioned ownership patterns and avoid parallel anchor models.

### Git Intelligence Summary

- Existing backend patterns are minimal-diff, contract-first, owner-scoped, and idempotency-aware.
- Existing screenshot lifecycle tests are comprehensive and should be extended, not replaced.
- OpenAPI response shaping and schema ref assertions are enforced centrally; anchor lifecycle updates must include those guards.

### Project Structure Notes

- No separate architecture artifact is required for this story; use OpenAPI + existing screenshot lifecycle implementation as primary guardrails.
- Keep Story 5.6 scoped to anchor create/list/get and cross-version traceability policy; export execution/provenance records are Epic 6 scope.

### References

- `spec/api/openapi.yaml` (`ScreenshotAnchorCreateRequest`, `AnchorAddress`, `AnchorResolution`, `/instructions/{instructionId}/anchors`, `/anchors/{anchorId}`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.6)
- `_bmad-output/planning-artifacts/prd.md` (FR-037, FR-038, deterministic traceability requirements)
- `spec/acceptance/tasks_codex_v1.md` (Task 12 anchor lifecycle scope)
- `spec/acceptance/v1_mvp.md` (anchor lifecycle acceptance surface)
- `_bmad-output/project-context.md` (contract-first API, ownership/no-leak policy, idempotency guidance)
- `_bmad-output/implementation-artifacts/5-5-annotation-operations-schema-and-deterministic-rendering.md`
- `apps/api/app/main.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`
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
- `spec/acceptance/v1_mvp.md`
- `_bmad-output/project-context.md`

### Completion Notes List

- 2026-03-02: Created Story 5.6 artifact with AC-mapped tasks for anchor create/list/get and cross-version resolution policy.
- 2026-03-02: Captured contract endpoints, query parameters, schema requirements, and no-leak ownership constraints from OpenAPI.
- 2026-03-02: Added testing and verification gates aligned to project quality policy (`make lint`, `make test`, `make check`).
- 2026-03-02: Implemented `POST /instructions/{instructionId}/anchors`, `GET /instructions/{instructionId}/anchors`, and `GET /anchors/{anchorId}` with owner-scoped no-leak `404` behavior.
- 2026-03-02: Added anchor addressing validation (`block_id` primary, `char_range` fallback), deterministic addressing strategy persistence, and instruction-version context checks.
- 2026-03-02: Implemented deterministic v1 cross-version anchor resolution projection (`retain`, `remap`, `unresolved`) with trace evidence on get-anchor when target version context is supplied.
- 2026-03-02: Extended anchor list/get to return contract-aligned asset/reference data, including `instruction_version_id` and `include_deleted_assets` filtering for list responses.
- 2026-03-02: Updated OpenAPI shaping/validation safeguards to include anchor lifecycle paths, schemas, and no-leak validation error mapping.
- 2026-03-02: Added API and unit coverage for create/list/get lifecycle behavior, validation/no-leak handling, and resolution trace structure; verified with `make lint`, `make test`, and `make check` in `apps/api`.
- 2026-03-02: Code review follow-up fixes applied: anchor-create now validates `block_id` existence in the source instruction and rejects out-of-bounds `char_range` values at write time.
- 2026-03-02: Added regression tests for semantic addressing validation to prevent orphaned anchors with unresolved source references.

### File List

- `_bmad-output/implementation-artifacts/5-6-anchor-addressing-persistence-policy-and-cross-version-traceability.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/main.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-03-02: Created Story 5.6 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-02: Implemented Story 5.6 anchor lifecycle, addressing persistence validation, cross-version resolution projection, and AC-mapped tests; moved story status to `review`.
- 2026-03-02: Completed Senior Developer code review fixes for semantic anchor addressing validation and moved story status to `done`.

## Senior Developer Review (AI)

- Reviewer: `founder`
- Date: `2026-03-02`
- Outcome: `Approve`

### Summary

- Validated Story 5.6 implementation against ACs and contract paths.
- Identified and fixed semantic addressing validation gaps in anchor create flow.
- Confirmed regression coverage now protects `block_id` existence and `char_range` bounds at write time.

### Findings Addressed

- `HIGH`: Anchor create accepted non-existent `block_id` values; fixed by validating against source instruction block IDs.
- `HIGH`: Anchor create accepted out-of-bounds `char_range`; fixed by validating bounds against source instruction markdown length.
- `MEDIUM`: Missing regression coverage for the above semantic checks; fixed with API and unit tests.
- `MEDIUM`: Working tree included unrelated pre-existing modified files not in this story scope; review confirmed story File List remains limited to Story 5.6 change set.

### Verification

- `make lint` (apps/api): pass
- `make test` (apps/api): pass (`174` tests)
- `make check` (apps/api): pass
