# Implementation Kickoff: High-Risk Endpoint Test Checklist (Given/When/Then)

**Date:** 2026-02-22  
**Project:** Howera  
**Source Contract:** `spec/api/openapi.yaml`  
**Priority Focus:** callbacks idempotency/order, FSM invalid transitions, version conflicts, export identity/provenance freeze, anchor persistence

## Test Harness Preconditions

- Use isolated fixtures per test: `project_id`, `job_id`, `instruction_id`, `instruction_version_id`, `anchor_id`, `export_id`.
- Capture both API response and persistent side effects (status row/version row/dispatch row/audit row).
- For no-mutation tests, assert unchanged: `status`, `manifest`, `failure fields`, `version`, and `updated_at` where applicable.
- For idempotency tests, assert exactly-one side effect (single dispatch, single state transition, single export record).
- For no-leak tests, validate unauthorized and nonexistent resources both return `404 RESOURCE_NOT_FOUND`.
- Add log assertions for sensitive data rules (no secrets, no raw transcript, no raw prompt content).

## `POST /internal/jobs/{jobId}/status` (P0)

- [ ] **CB-001 First callback accepted**
  - Given a valid callback secret and a job in a state that allows transition to payload `status`
  - When callback is submitted with unique `(job_id,event_id)` and valid `occurred_at`
  - Then response is `204`
  - And exactly one state transition is persisted.

- [ ] **CB-002 Replay identical payload is no-op**
  - Given a previously accepted callback `(job_id,event_id)`
  - When the same payload is submitted again
  - Then response is `200` with `replayed=true`
  - And no additional state/artifact/failure writes occur
  - And no duplicate transition audit event is emitted.

- [ ] **CB-003 Replay with payload mismatch rejected**
  - Given a previously accepted `(job_id,event_id)`
  - When the same `event_id` is sent with different payload content
  - Then response is `409` with `code=EVENT_ID_PAYLOAD_MISMATCH`
  - And no mutation is persisted.

- [ ] **CB-004 Out-of-order callback rejected**
  - Given a latest applied callback timestamp newer than incoming `occurred_at`
  - When incoming callback implies backward/non-monotonic transition
  - Then response is `409` with `code=CALLBACK_OUT_OF_ORDER`
  - And response includes `latest_applied_occurred_at`, `current_status`, `attempted_status`
  - And no mutation is persisted.

- [ ] **CB-005 Invalid FSM transition rejected**
  - Given a callback status not allowed by FSM from current job status
  - When callback is submitted
  - Then response is `409` with `code=FSM_TRANSITION_INVALID` (or `FSM_TERMINAL_IMMUTABLE` for terminal mutation)
  - And `details` includes `current_status`, `attempted_status`.

- [ ] **CB-006 Transactional write guarantee**
  - Given callback includes status update + `artifact_updates` + failure metadata
  - When persistence is fault-injected at one write boundary
  - Then all side effects are rolled back atomically
  - And manifest is merge-safe (unrelated keys preserved; immutable raw artifacts not overwritten/deleted).

- [ ] **CB-007 Callback auth enforced**
  - Given invalid or missing callback secret
  - When callback is submitted
  - Then response is `401`
  - And no mutation is persisted.

- [ ] **CB-008 No-leak policy**
  - Given unauthorized job ID and nonexistent job ID cases
  - When callback endpoint is called
  - Then both return `404 RESOURCE_NOT_FOUND`
  - And ownership/resource existence is not disclosed.

## `POST /jobs/{jobId}/confirm-upload` (P0)

- [ ] **CU-001 Valid confirm transition**
  - Given owned job in confirm-eligible state and valid `video_uri`
  - When confirm-upload is called
  - Then response is `200`
  - And job transitions to `UPLOADED`
  - And `manifest.video_uri` equals submitted value exactly.

- [ ] **CU-002 Idempotent same `video_uri`**
  - Given confirm-upload was already completed for the same `video_uri`
  - When confirm-upload is called again with same URI
  - Then response is `200` with `replayed=true`
  - And no duplicate writes or extra state transitions occur.

- [ ] **CU-003 Conflicting `video_uri` rejected**
  - Given confirm-upload already stored `video_uri=A`
  - When confirm-upload is called with `video_uri=B`
  - Then response is `409` with `code=VIDEO_URI_CONFLICT`
  - And no mutation occurs.

- [ ] **CU-004 Invalid FSM transition rejected**
  - Given job in a state where transition to `UPLOADED` is invalid
  - When confirm-upload is called
  - Then response is `409` with `code=FSM_TRANSITION_INVALID`
  - And `details.current_status` / `details.attempted_status` are present.

## `POST /jobs/{jobId}/run` (P0)

- [ ] **RUN-001 Eligible run dispatches exactly once**
  - Given owned job in `UPLOADED` state
  - When run is requested
  - Then response is `202`
  - And exactly one orchestrator dispatch is created
  - And dispatch payload includes `job_id`, `project_id`, `video_uri`, `callback_url`.

- [ ] **RUN-002 Ineligible state rejected**
  - Given owned job not in `UPLOADED`
  - When run is requested
  - Then response is `409` with `code=FSM_TRANSITION_INVALID`
  - And no dispatch occurs.

- [ ] **RUN-003 Run idempotency**
  - Given run was already accepted for job
  - When run is called repeatedly
  - Then response is `200` replay form
  - And returned `dispatch_id` is identical
  - And duplicate orchestrator executions are not created.

- [ ] **RUN-004 Dispatch failure handling**
  - Given orchestrator dependency is unavailable
  - When run is requested
  - Then response is `502` with `code=ORCHESTRATOR_DISPATCH_FAILED`
  - And job state is not advanced.

## `POST /jobs/{jobId}/cancel` (P1)

- [ ] **CAN-001 Cancellable state succeeds**
  - Given owned job in an FSM-cancellable state
  - When cancel is requested
  - Then response is `200`
  - And status becomes `CANCELLED`.

- [ ] **CAN-002 Non-cancellable state rejected**
  - Given owned job in a non-cancellable state
  - When cancel is requested
  - Then response is `409` with `code=FSM_TRANSITION_INVALID`
  - And `details.attempted_status` is `CANCELLED`
  - And no mutation occurs.

## `POST /jobs/{jobId}/retry` (P0)

- [ ] **RET-001 Retry allowed only from FAILED**
  - Given job status is not `FAILED`
  - When retry is requested
  - Then response is `409` with `code=RETRY_NOT_ALLOWED_STATE`
  - And no dispatch occurs.

- [ ] **RET-002 Block retry when already running/dispatched**
  - Given job has active execution/dispatched state
  - When retry is requested
  - Then response is `409` with `code=JOB_ALREADY_RUNNING`
  - And no new dispatch occurs.

- [ ] **RET-003 Valid retry persists recovery metadata**
  - Given job in `FAILED` with checkpoint history
  - When retry is requested with valid `model_profile` and `client_request_id`
  - Then response is `202`
  - And `resume_from_status`, `checkpoint_ref`, and `model_profile` are persisted
  - And dispatch payload includes those fields plus `job_id`, `project_id`, `video_uri`, `callback_url`.

- [ ] **RET-004 Retry idempotency by `client_request_id`**
  - Given retry accepted for `(job_id, client_request_id)`
  - When same request is replayed
  - Then response is `200` with `replayed=true`
  - And returned `dispatch_id` matches the original
  - And no duplicate dispatch is created.

- [ ] **RET-005 Retry dispatch failure does not advance state**
  - Given job in `FAILED` and orchestrator dispatch fails
  - When retry is requested
  - Then response is `502` with `code=ORCHESTRATOR_DISPATCH_FAILED`
  - And state remains unchanged.

## `PUT /instructions/{instructionId}` (P0)

- [ ] **INS-001 Optimistic concurrency success**
  - Given current instruction version `N`
  - When update is sent with `base_version=N`
  - Then response is `200`
  - And new persisted version is `N+1`
  - And response includes `instruction_id`, `job_id`, `version`, `updated_at`, `validation_status`.

- [ ] **INS-002 Stale base version rejected**
  - Given current instruction version `N+1`
  - When update is sent with `base_version=N`
  - Then response is `409` with `code=VERSION_CONFLICT`
  - And `details.base_version` and `details.current_version` are returned
  - And no mutation occurs.

## `POST /instructions/{instructionId}/regenerate` (P1)

- [ ] **REG-001 Selection addressing validation**
  - Given regenerate payload missing both `block_id` and `char_range`
  - When regenerate is requested
  - Then response is `400` with `code=VALIDATION_ERROR`
  - And no task is created.

- [ ] **REG-002 Regenerate idempotency**
  - Given accepted regenerate for `(instruction_id, client_request_id)`
  - When same request is replayed
  - Then response is `200`
  - And same task ID is returned
  - And duplicate work is not created.

- [ ] **REG-003 Regenerate provenance persistence**
  - Given valid regenerate request
  - When request is accepted
  - Then response is `202`
  - And provenance stores `instruction_id`, `base_version`, `selection`, `requested_by`, `requested_at`
  - And stores `model_profile` / prompt refs when provided.

- [ ] **REG-004 Version conflict protection**
  - Given stale `base_version` in regenerate request
  - When regenerate is requested
  - Then response is `409` with `code=VERSION_CONFLICT`
  - And no task is created.

## `GET /tasks/{taskId}` (P1)

- [ ] **TASK-001 SUCCEEDED returns new instruction version ref**
  - Given regenerate task completed successfully
  - When task status is requested
  - Then response is `200`
  - And includes `instruction_id` and `instruction_version`.

- [ ] **TASK-002 FAILED response is sanitized**
  - Given regenerate task failed
  - When task status is requested
  - Then response is `200`
  - And includes safe failure fields (`failure_code`, `failure_message`, `failed_stage`)
  - And excludes secrets, raw transcript, and prompt content.

## `POST /jobs/{jobId}/exports` (P0)

- [ ] **EXP-001 Identity key determinism**
  - Given valid export request with `instruction_version_id` and `format`
  - When export is requested
  - Then response is `202` and export record is created
  - And `identity_key` equals deterministic tuple (`instruction_version_id + format + screenshot_set_hash`)
  - And status starts at `REQUESTED`.

- [ ] **EXP-002 Export request idempotency**
  - Given an existing export for same identity key
  - When same export request is submitted again
  - Then response is `200`
  - And same `export_id` is returned
  - And no duplicate export record/workflow is created.

- [ ] **EXP-003 Invalid request rejected with no record**
  - Given invalid `instruction_version_id` or unsupported format
  - When export is requested
  - Then response is `400` with `code=EXPORT_REQUEST_INVALID`
  - And no export record is created.

- [ ] **EXP-004 Provenance snapshot completeness**
  - Given valid export request
  - When export record is created
  - Then provenance includes `instruction_version_id`, `screenshot_set_hash`, anchor set, `active_asset_id`, `rendered_asset_id` where present
  - And uses stored instruction snapshot + model/prompt references by ID only.

## `GET /exports/{exportId}` (P0)

- [ ] **EXPG-001 Export FSM surface**
  - Given export in each phase (`REQUESTED`, `RUNNING`, `SUCCEEDED`, `FAILED`)
  - When status is requested
  - Then response is `200`
  - And `status` reflects one of those states only.

- [ ] **EXPG-002 Provenance freeze on success**
  - Given export transitions to `SUCCEEDED`
  - When status is requested
  - Then `provenance_frozen_at` is populated
  - And subsequent retrievals show identical provenance/identity fields.

- [ ] **EXPG-003 Signed URL policy**
  - Given export `SUCCEEDED`
  - When status is requested
  - Then `download_url` is present and scoped to the export artifact
  - And `download_url_expires_at` is present.

- [ ] **EXPG-004 No signed URL before success**
  - Given export state is `REQUESTED`, `RUNNING`, or `FAILED`
  - When status is requested
  - Then `download_url` is absent or unusable.

## `POST /instructions/{instructionId}/anchors` (P0)

- [ ] **ANC-001 Primary addressing create (`block_id`)**
  - Given valid instruction version and `addressing.address_type=block_id`
  - When anchor is created
  - Then response is `201`
  - And anchor stores addressing type/value and strategy metadata.

- [ ] **ANC-002 Fallback addressing create (`char_range`)**
  - Given valid instruction version and `addressing.address_type=char_range`
  - When anchor is created
  - Then response is `201`
  - And anchor stores exact `char_range`.

## `GET /instructions/{instructionId}/anchors` (P0)

- [ ] **ANL-001 Version-scoped listing**
  - Given anchors across multiple instruction versions
  - When listing with `instruction_version_id`
  - Then only anchors bound to requested version are returned.

- [ ] **ANL-002 Deleted asset handling in list**
  - Given an anchor with soft-deleted asset versions
  - When listing with default `include_deleted_assets=false`
  - Then deleted asset versions are excluded from active selection.

## `GET /anchors/{anchorId}` (P0)

- [ ] **ANG-001 Anchor resolution classification**
  - Given anchor queried with `target_instruction_version_id`
  - When resolution is computed
  - Then response includes `resolution.resolution_state` in `retain|remap|unresolved`
  - And includes trace metadata linking source and target instruction versions.

## `POST /anchors/{anchorId}/replace` (P1)

- [ ] **ANR-001 Replace creates new asset version linkage**
  - Given anchor has active asset version `V`
  - When replace request succeeds
  - Then response is `202` (or `200` replay)
  - And resulting active asset version is `V+1`
  - And `previous_asset_id` links to former active asset.

- [ ] **ANR-002 Replace idempotency**
  - Given same canonical extraction inputs/idempotency key
  - When replace is repeated
  - Then response is `200` replay form
  - And no additional asset version is created.

## `DELETE /anchors/{anchorId}/assets/{assetId}` (P1)

- [ ] **AND-001 Soft-delete active asset fallback**
  - Given deleted asset is current `active_asset_id`
  - When delete is requested
  - Then response is `200`
  - And `active_asset_id` falls back to previous valid version or `null`.

- [ ] **AND-002 Deleted history remains queryable**
  - Given soft-deleted asset versions exist
  - When anchor history is queried via include-deleted path
  - Then deleted versions remain retrievable and marked non-active.

## `POST /anchors/{anchorId}/annotations` (P1)

- [ ] **ANN-001 Deterministic annotation render**
  - Given valid operations list (`op_type`, `geometry`, `style`)
  - When annotate is requested
  - Then response is `200`
  - And `ops_hash` deterministically maps to `rendered_asset_id`.

- [ ] **ANN-002 Annotation idempotent replay**
  - Given identical base asset + normalized operations submitted again
  - When annotate is requested
  - Then same `rendered_asset_id` is returned
  - And duplicate render work is not created.

- [ ] **ANN-003 Render failure rollback**
  - Given render pipeline fails mid-operation
  - When annotate is requested
  - Then prior active annotation state remains unchanged
  - And no partial mutation is persisted.

## Cross-Cutting Assertions (P0)

- [ ] **X-001 No-leak policy consistency**
  - Given unauthorized and nonexistent resources
  - When invoking protected endpoints in this checklist
  - Then both cases return identical `404 RESOURCE_NOT_FOUND` behavior.

- [ ] **X-002 Sensitive logging constraints**
  - Given all error/failure/replay paths in this checklist
  - When logs are captured
  - Then logs contain no secrets, raw transcript content, or raw prompt content.

- [ ] **X-003 Audit consistency (business-transition only)**
  - Given idempotent replay requests
  - When replay paths execute
  - Then duplicate business audit events are suppressed
  - And transition/export/regenerate events contain required metadata fields.
