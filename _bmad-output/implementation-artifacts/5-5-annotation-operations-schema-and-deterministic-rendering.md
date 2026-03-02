# Story 5.5: Annotation Operations Schema and Deterministic Rendering

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want annotation edits stored as operation log and deterministic rendered output,
so that visual modifications are reproducible and auditable.

## Acceptance Criteria

1. Given annotation request on an owned base asset, when payload is validated, then operations conform to schema (`op_type`, `geometry`, `style`, ordering), and invalid operations are rejected with contract-defined validation error.
2. Given valid operation set, when render pipeline executes, then deterministic rendering key `ops_hash` is computed from base asset and normalized operations, and rendered output maps to `rendered_asset_id` deterministically.
3. Given identical `ops_hash` is submitted again, when processed, then operation is idempotent, and existing `rendered_asset_id` is returned without duplicate render.
4. Given render failure occurs, when transaction finalizes, then prior active annotation state remains unchanged, and no partial anchor or asset mutation is persisted.

## Tasks / Subtasks

- [x] Implement annotation contract models and route/service boundary (AC: 1, 2, 3, 4)
- [x] Add request/response schemas aligned to OpenAPI: `AnnotationOperation`, `AnnotateScreenshotRequest`, `AnnotateScreenshotResponse`.
- [x] Implement `POST /anchors/{anchorId}/annotations` as a thin route handler with service-owned ownership/no-leak behavior.
- [x] Keep response sets contract-safe for annotation endpoint (`200/400/404`) and no write-side effects on reject paths.
- [x] Implement operation schema validation and normalization pipeline (AC: 1)
- [x] Enforce op schema: `op_type` in `blur|arrow|marker|pencil`, operation list `minItems=1`, and object payload structure for `geometry`/`style`.
- [x] Implement deterministic normalization for operation ordering and key ordering before hashing.
- [x] Reject invalid payloads with contract-safe validation behavior and no persistence side effects.
- [x] Implement deterministic rendering identity and idempotent replay semantics (AC: 2, 3)
- [x] Compute `ops_hash` from `anchor_id + base_asset_id + normalized_operations` (stable canonical representation).
- [x] Persist rendered asset linkage with `ops_hash`, `rendered_asset_id`, and `rendered_from_asset_id`.
- [x] Replay identical requests to return existing `rendered_asset_id` without duplicate render/mutation.
- [x] Implement transactional mutation safety on render failure (AC: 4)
- [x] Ensure anchor `active_asset_id` and asset-version chain updates are committed only after render success.
- [x] Add rollback/no-partial-state guarantees for render failure paths.
- [x] Preserve ownership scoping and no-leak `404` semantics for missing/cross-owner anchor or base asset.
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2, 3, 4)
- [x] Add API tests for happy path (`200`) with expected response fields (`anchor_id`, `base_asset_id`, `ops_hash`, `rendered_asset_id`, `active_asset_id`).
- [x] Add API tests for invalid operation payloads returning `400` and no side effects.
- [x] Add API tests for cross-owner/missing anchor and base-asset context returning no-leak `404`.
- [x] Add API and unit tests for idempotent replay behavior on identical normalized operations.
- [x] Add unit tests for deterministic `ops_hash` generation across semantically identical payload orderings.
- [x] Add unit tests that injected render failure leaves anchor active state and asset store unchanged.
- [x] Re-verify `/openapi.json` includes `/anchors/{anchorId}/annotations` with expected request/response schema refs and `200/400/404`.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 5.4 completed signed upload ticket integrity checks, deterministic attach replay behavior, and contract-safe nullability shaping.
- Story 5.5 extends screenshot lifecycle with annotation render semantics on top of established owner/no-leak, version chain, and idempotency patterns from Stories 5.1-5.4.
- Contract-first scope is strict: no new endpoint/status/schema outside `spec/api/openapi.yaml`.

### Technical Requirements

- Endpoint in scope:
- `POST /anchors/{anchorId}/annotations`
- Contract behavior from OpenAPI:
- `200`: `AnnotateScreenshotResponse`
- `400`: `Error` for invalid operations
- `404`: no-leak for unauthorized or missing anchor/asset context
- Schema requirements from OpenAPI:
- `AnnotateScreenshotRequest`: `base_asset_id` (string), `operations` (array, `minItems: 1`), optional `idempotency_key`
- `AnnotationOperation`: required `op_type`, `geometry`, `style`; `op_type` enum is `blur|arrow|marker|pencil`
- `AnnotateScreenshotResponse`: required `anchor_id`, `base_asset_id`, `ops_hash`, `rendered_asset_id`, `active_asset_id`
- Determinism requirements:
- `ops_hash` must be stable for semantically identical operation sets after normalization.
- Repeated identical requests must be replay-safe and return existing render linkage.
- Failure safety requirements:
- On render failure, anchor active state and asset history must remain unchanged.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep route handlers thin; implement ownership checks, validation, deterministic hashing, replay semantics, and mutation safety in service/repository layers.
- Preserve no-existence-leak behavior (`404`) for missing and unauthorized resources.
- Preserve artifact discipline:
- raw artifacts remain immutable.
- rendered annotation outputs are derived/versioned assets with explicit linkage metadata (`ops_hash`, `rendered_from_asset_id`).
- Do not bypass adapter boundaries for external rendering dependencies if introduced.

### Library & Framework Requirements

- FastAPI + Pydantic remain contract authority for request/response modeling.
- Reuse screenshot lifecycle persistence/service patterns already used for extract/replace/delete/upload/attach.
- Reuse OpenAPI shaping + request-validation handling in `app/main.py` and contract assertions in `test_auth_middleware.py`.
- No new dependencies expected for v1 in-memory implementation; keep deterministic hashing and normalization in pure Python.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/schemas/job.py` (annotation request/response models)
- `apps/api/app/routes/jobs.py` (add `POST /anchors/{anchorId}/annotations`)
- `apps/api/app/services/jobs.py` (annotation orchestration, ownership/no-leak behavior, idempotency/replay handling)
- `apps/api/app/repositories/memory.py` (operation normalization, `ops_hash` generation, deterministic render linkage persistence, rollback-safe mutation path)
- `apps/api/app/main.py` (OpenAPI response-code allowlist and annotation schema shaping)
- `apps/api/tests/test_jobs_ownership.py` (API/unit coverage for annotation validation, idempotency, rollback safety)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI path/schema assertions for annotation endpoint)

### Testing Requirements

- Validate happy path returns `200` with contract-required `AnnotateScreenshotResponse` fields.
- Validate invalid annotation operations return `400` with no anchor/asset mutation.
- Validate no-leak `404` for missing/cross-owner anchor and base asset.
- Validate deterministic `ops_hash` is stable for equivalent normalized operation sets.
- Validate replay of identical annotation payload returns existing `rendered_asset_id` without duplicate derived asset creation.
- Validate render failure path leaves pre-existing active asset and version chain unchanged.
- Validate `/openapi.json` includes `/anchors/{anchorId}/annotations` with expected request/response refs and `200/400/404`.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 5.4 delivered:
- signed upload URL integrity checks and confirm-time signature enforcement.
- deterministic attach replay that preserves original instruction-version snapshot semantics.
- contract-safe response shaping (`response_model_exclude_none`) and OpenAPI nullability alignment for screenshot assets.
- Story 5.5 should keep these deterministic/idempotent patterns and avoid any side effects on rejected requests.

### Git Intelligence Summary

- Recent commit history reflects contract-first, endpoint-scoped implementation increments (latest visible: `4-3-update-instruction-markdown-with-versioning-and-concurrency-control`).
- Existing code patterns in this repository favor:
- thin routes with service-owned control flow
- deterministic repository updates and idempotent replay maps
- explicit no-leak ownership checks
- OpenAPI schema/ref enforcement in middleware tests
- Follow the same minimal-diff style for Story 5.5.

### Project Structure Notes

- No standalone `architecture.md` or UX artifact is present under `_bmad-output/planning-artifacts/`; use `epics.md`, `prd.md`, OpenAPI, and existing screenshot lifecycle code as primary guardrails.
- Keep Story 5.5 limited to annotation operation validation + deterministic rendering semantics; cross-version anchor persistence policy belongs to Story 5.6.

### References

- `spec/api/openapi.yaml` (`AnnotationOperation`, `AnnotateScreenshotRequest`, `AnnotateScreenshotResponse`, `/anchors/{anchorId}/annotations`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.5)
- `_bmad-output/planning-artifacts/prd.md` (FR-036 screenshot annotations)
- `spec/acceptance/tasks_codex_v1.md` (Task 14 annotation operation log + deterministic render)
- `_bmad-output/project-context.md` (contract-first API, idempotency, artifact discipline, no-leak policy)
- `_bmad-output/implementation-artifacts/5-4-upload-custom-image-via-signed-url-and-confirm-attach.md`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_jobs_ownership.py`
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
- `_bmad-output/implementation-artifacts/5-4-upload-custom-image-via-signed-url-and-confirm-attach.md`

### Completion Notes List

- 2026-03-02: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-02: Story seeded with AC-mapped annotation tasks, deterministic render/idempotency guardrails, and rollback-safety test requirements.
- 2026-03-02: Implemented `POST /anchors/{anchorId}/annotations` with contract-safe `200/400/404` handling, owner/no-leak checks, deterministic operation normalization, and stable `ops_hash`/`rendered_asset_id` mapping.
- 2026-03-02: Added repository-level annotation replay maps, idempotency-key mismatch protection, and render-failure failpoint behavior that preserves prior anchor/asset state.
- 2026-03-02: Added API/unit/OpenAPI coverage for happy path, invalid payload no-mutation, no-leak `404`, normalized replay determinism, and render-failure rollback safety.
- 2026-03-02: Verification completed in `apps/api` via `make lint`, `make test`, `make check`; explicitly confirmed `/openapi.json` includes `/api/v1/anchors/{anchorId}/annotations` with expected refs and `200/400/404`.

### File List

- `_bmad-output/implementation-artifacts/5-5-annotation-operations-schema-and-deterministic-rendering.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/schemas/job.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Change Log

- 2026-03-02: Created Story 5.5 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-02: Corrected Epic 5 status to `in-progress` because unfinished stories remain in the epic.
- 2026-03-02: Completed Story 5.5 implementation and set story status to `done` with passing verification gates.
