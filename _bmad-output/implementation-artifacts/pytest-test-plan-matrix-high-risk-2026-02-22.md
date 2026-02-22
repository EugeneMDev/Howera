# Pytest Test Plan Matrix (High-Risk)

**Date:** 2026-02-22  
**Project:** Howera  
**Source:** `spec/api/openapi.yaml` and `_bmad-output/implementation-artifacts/endpoint-test-checklist-high-risk-2026-02-22.md`

## Scope and Priority

This matrix translates the high-risk checklist into pytest-ready endpoint tests.  
`P0` cases are the release-blocking set.

## Fixture Inventory

| fixture | scope | provides | notes |
| --- | --- | --- | --- |
| `auth_editor_a` | function | Bearer token for owner/editor A | Default authenticated actor |
| `auth_editor_b` | function | Bearer token for non-owner/editor B | Used for no-leak tests |
| `callback_secret_valid` | function | Valid `X-Callback-Secret` header | Internal callback auth |
| `callback_secret_invalid` | function | Invalid callback header | Callback 401 test |
| `project_a` | function | Owned project record | Base ownership fixture |
| `job_uploaded` | function | Job in `UPLOADED` with `video_uri` | Run + confirm replay tests |
| `job_non_uploaded` | function | Job not in `UPLOADED` | FSM 409 tests |
| `job_failed_checkpointed` | function | Job in `FAILED` with checkpoint metadata | Retry success path |
| `job_running` | function | Job currently running/dispatched | Retry `JOB_ALREADY_RUNNING` |
| `job_terminal_done` | function | Job in `DONE` | Terminal FSM invalid tests |
| `instruction_vn` | function | Instruction with current version `N` and markdown | Versioning tests |
| `instruction_vn_plus_1` | function | Instruction advanced to `N+1` | Stale base-version tests |
| `regen_request_valid` | function | Valid regenerate payload with `client_request_id` | Regenerate happy path |
| `regen_request_stale` | function | Regenerate payload with stale `base_version` | Regenerate 409 path |
| `callback_event_base` | function | Canonical callback payload with `(job_id,event_id)` | Callback first-apply/replay |
| `callback_event_mismatch` | function | Same `event_id`, altered payload | `EVENT_ID_PAYLOAD_MISMATCH` |
| `callback_event_out_of_order` | function | Older `occurred_at` causing non-monotonic transition | `CALLBACK_OUT_OF_ORDER` |
| `orchestrator_spy` | function | Dispatch spy/call counter | Exactly-once dispatch assertions |
| `orchestrator_fail` | function | Orchestrator failure injection | `502 ORCHESTRATOR_DISPATCH_FAILED` |
| `idempotency_store_reader` | function | Read-only accessor for idempotency records | Assert `(job_id,event_id)` uniqueness |
| `audit_reader` | function | Accessor for audit events | Required fields + no duplicate business events |
| `log_capture` | function | Structured log capture | Sensitive content assertions |
| `db_snapshot` | function | Snapshot helper (`before/after`) | No-mutation and atomicity checks |
| `export_request_valid` | function | Export request (`instruction_version_id`, `format`) | Export identity/provenance tests |
| `export_request_same_identity` | function | Duplicate export request for same identity tuple | Export idempotency |
| `export_record_succeeded` | function | Export in `SUCCEEDED` with frozen provenance | GET export assertions |
| `settings_export_ttl` | session | Configured download URL TTL seconds | TTL bound assertion |
| `anchor_block_id` | function | Anchor addressed via `block_id` | Anchor create/get tests |
| `anchor_char_range` | function | Anchor addressed via `char_range` | Fallback addressing tests |
| `anchor_with_asset_chain` | function | Anchor with active asset + previous versions | Replace/delete determinism |
| `annotation_ops_normalized` | function | Deterministic normalized annotation ops | `ops_hash` determinism |
| `render_fail_injection` | function | Controlled render failure hook | Annotation rollback test |
| `clock_freeze` | function | Deterministic time control | Callback ordering + URL expiry checks |

## Suggested `tests/` Module Layout

```text
tests/
  conftest.py
  fixtures/
    auth_fixtures.py
    job_fixtures.py
    instruction_fixtures.py
    export_fixtures.py
    anchor_fixtures.py
    callback_fixtures.py
  support/
    api_client.py
    assertions_state.py
    assertions_audit.py
    assertions_logs.py
    orchestrator_spy.py
  api/
    test_internal_callbacks_high_risk.py
    test_jobs_fsm_and_idempotency_high_risk.py
    test_instructions_versioning_high_risk.py
    test_exports_determinism_high_risk.py
    test_anchors_assets_determinism_high_risk.py
  integration/
    test_no_leak_and_sensitive_logging_high_risk.py
```

Suggested markers:
- `@pytest.mark.p0` for release-blocking tests
- `@pytest.mark.p1` for important but non-blocking tests
- `@pytest.mark.high_risk` for the full matrix suite

## Matrix: Internal Callback Idempotency, Ordering, Atomicity

| test_id | priority | endpoint/method | fixtures | request | expected_status | assertions (+ audit/idempotency notes) |
| --- | --- | --- | --- | --- | --- | --- |
| `CB_001` | P0 | `POST /internal/jobs/{jobId}/status` | `auth_editor_a`, `callback_secret_valid`, `job_non_uploaded`, `callback_event_base`, `audit_reader`, `idempotency_store_reader` | `{"event_id":"evt-1","status":"AUDIO_READY","occurred_at":"T1","correlation_id":"corr-1"}` | `204` | State transitions once; idempotency record `(job_id,evt-1)` created; exactly one transition audit event with required fields. |
| `CB_002` | P0 | `POST /internal/jobs/{jobId}/status` | `callback_secret_valid`, `callback_event_base`, `db_snapshot`, `audit_reader` | Replay exact payload for `(job_id,evt-1)` | `200` | `replayed=true`; no state/manifest/failure writes; no duplicate transition audit event. |
| `CB_003` | P0 | `POST /internal/jobs/{jobId}/status` | `callback_secret_valid`, `callback_event_mismatch`, `db_snapshot` | Same `event_id`, different payload hash | `409` | `code=EVENT_ID_PAYLOAD_MISMATCH`; zero mutation vs snapshot. |
| `CB_004` | P0 | `POST /internal/jobs/{jobId}/status` | `callback_secret_valid`, `callback_event_out_of_order`, `clock_freeze`, `db_snapshot` | Older `occurred_at` causing backward transition | `409` | `code=CALLBACK_OUT_OF_ORDER`; `details.latest_applied_occurred_at/current_status/attempted_status` present; no mutation. |
| `CB_005` | P0 | `POST /internal/jobs/{jobId}/status` | `callback_secret_valid`, `job_terminal_done`, `db_snapshot` | Attempt terminal-state mutation via callback | `409` | `code=FSM_TERMINAL_IMMUTABLE` or `FSM_TRANSITION_INVALID`; includes transition details; no mutation. |
| `CB_006` | P0 | `POST /internal/jobs/{jobId}/status` | `callback_secret_valid`, `callback_event_base`, `db_snapshot`, `orchestrator_spy` | Payload with `artifact_updates` + failure fields under fault injection | `500` (injected) | Atomic rollback: no partial status/manifest/failure persistence; manifest keys unchanged for immutable raw artifacts. |
| `CB_007` | P0 | `POST /internal/jobs/{jobId}/status` | `callback_secret_invalid`, `db_snapshot` | Valid payload with invalid callback secret | `401` | No idempotency/state/audit writes. |
| `CB_008` | P0 | `POST /internal/jobs/{jobId}/status` | `callback_secret_valid`, `auth_editor_b` | Unauthorized job vs nonexistent job | `404` | Both cases return same no-leak shape (`RESOURCE_NOT_FOUND`), no existence disclosure. |

## Matrix: FSM 409 Semantics and Job Idempotency

| test_id | priority | endpoint/method | fixtures | request | expected_status | assertions (+ audit/idempotency notes) |
| --- | --- | --- | --- | --- | --- | --- |
| `CU_001` | P0 | `POST /jobs/{jobId}/confirm-upload` | `auth_editor_a`, `job_non_uploaded` | `{"video_uri":"gs://bucket/video-a.mp4"}` | `200` | Job transitions to `UPLOADED`; manifest stores exact URI. |
| `CU_002` | P0 | `POST /jobs/{jobId}/confirm-upload` | `auth_editor_a`, `job_uploaded`, `db_snapshot` | Replay same `video_uri` | `200` | `replayed=true`; no extra writes/transitions. |
| `CU_003` | P0 | `POST /jobs/{jobId}/confirm-upload` | `auth_editor_a`, `job_uploaded`, `db_snapshot` | Different `video_uri` than stored | `409` | `code=VIDEO_URI_CONFLICT`; no mutation. |
| `CU_004` | P0 | `POST /jobs/{jobId}/confirm-upload` | `auth_editor_a`, `job_terminal_done`, `db_snapshot` | Confirm from invalid state | `409` | `code=FSM_TRANSITION_INVALID` or terminal immutable code; transition details present. |
| `RUN_001` | P0 | `POST /jobs/{jobId}/run` | `auth_editor_a`, `job_uploaded`, `orchestrator_spy` | `{}` | `202` | Exactly one dispatch; payload has `job_id,project_id,video_uri,callback_url`. |
| `RUN_002` | P0 | `POST /jobs/{jobId}/run` | `auth_editor_a`, `job_non_uploaded`, `orchestrator_spy` | `{}` | `409` | `code=FSM_TRANSITION_INVALID`; no dispatch. |
| `RUN_003` | P0 | `POST /jobs/{jobId}/run` | `auth_editor_a`, `job_uploaded`, `orchestrator_spy` | Repeat run request after `RUN_001` | `200` | Same `dispatch_id`; dispatch count remains 1. |
| `RUN_004` | P0 | `POST /jobs/{jobId}/run` | `auth_editor_a`, `job_uploaded`, `orchestrator_fail`, `db_snapshot` | `{}` | `502` | `code=ORCHESTRATOR_DISPATCH_FAILED`; state not advanced. |
| `CAN_002` | P0 | `POST /jobs/{jobId}/cancel` | `auth_editor_a`, `job_terminal_done`, `db_snapshot` | `{}` | `409` | `code=FSM_TRANSITION_INVALID`; `attempted_status=CANCELLED`; no mutation. |
| `RET_001` | P0 | `POST /jobs/{jobId}/retry` | `auth_editor_a`, `job_non_uploaded`, `db_snapshot` | `{"model_profile":"cloud-gpt","client_request_id":"retry-1"}` | `409` | `code=RETRY_NOT_ALLOWED_STATE`; no dispatch. |
| `RET_002` | P0 | `POST /jobs/{jobId}/retry` | `auth_editor_a`, `job_running`, `db_snapshot` | `{"model_profile":"cloud-gpt","client_request_id":"retry-2"}` | `409` | `code=JOB_ALREADY_RUNNING`; no dispatch. |
| `RET_003` | P0 | `POST /jobs/{jobId}/retry` | `auth_editor_a`, `job_failed_checkpointed`, `orchestrator_spy` | `{"model_profile":"cloud-gpt","client_request_id":"retry-3"}` | `202` | Persists `resume_from_status/checkpoint_ref/model_profile`; dispatch payload includes all required recovery fields. |
| `RET_004` | P0 | `POST /jobs/{jobId}/retry` | `auth_editor_a`, `job_failed_checkpointed`, `orchestrator_spy` | Replay same `client_request_id` | `200` | `replayed=true`; same `dispatch_id`; no duplicate dispatch. |
| `RET_005` | P0 | `POST /jobs/{jobId}/retry` | `auth_editor_a`, `job_failed_checkpointed`, `orchestrator_fail`, `db_snapshot` | `{"model_profile":"cloud-gpt","client_request_id":"retry-4"}` | `502` | `code=ORCHESTRATOR_DISPATCH_FAILED`; no state advance. |

## Matrix: Version Conflict 409 Semantics

| test_id | priority | endpoint/method | fixtures | request | expected_status | assertions (+ audit/idempotency notes) |
| --- | --- | --- | --- | --- | --- | --- |
| `INS_001` | P0 | `PUT /instructions/{instructionId}` | `auth_editor_a`, `instruction_vn` | `{"base_version":N,"markdown":"# updated"}` | `200` | New version `N+1`; response includes `instruction_id,job_id,version,updated_at,validation_status`. |
| `INS_002` | P0 | `PUT /instructions/{instructionId}` | `auth_editor_a`, `instruction_vn_plus_1`, `db_snapshot` | `{"base_version":N,"markdown":"# stale"}` | `409` | `code=VERSION_CONFLICT`; `details.base_version/current_version` populated; no mutation. |
| `REG_001` | P0 | `POST /instructions/{instructionId}/regenerate` | `auth_editor_a`, `instruction_vn` | Missing both `block_id` and `char_range` | `400` | `code=VALIDATION_ERROR`; no task row created. |
| `REG_002` | P0 | `POST /instructions/{instructionId}/regenerate` | `auth_editor_a`, `instruction_vn`, `regen_request_valid` | Valid request with `client_request_id=regen-1` | `202` | Task created with provenance (`instruction_id/base_version/selection/requested_by/requested_at` + optional model/prompt refs). |
| `REG_003` | P0 | `POST /instructions/{instructionId}/regenerate` | `auth_editor_a`, `instruction_vn`, `regen_request_valid` | Replay same `client_request_id=regen-1` | `200` | Same task ID returned; no duplicate work item. |
| `REG_004` | P0 | `POST /instructions/{instructionId}/regenerate` | `auth_editor_a`, `instruction_vn_plus_1`, `regen_request_stale`, `db_snapshot` | Stale `base_version` | `409` | `code=VERSION_CONFLICT`; no task created. |
| `TASK_001` | P0 | `GET /tasks/{taskId}` | `auth_editor_a`, `regen_request_valid` | Poll task in `SUCCEEDED` | `200` | Includes `instruction_id` + `instruction_version` reference to new version. |
| `TASK_002` | P0 | `GET /tasks/{taskId}` | `auth_editor_a`, `regen_request_valid`, `log_capture` | Poll task in `FAILED` | `200` | Only sanitized `failure_code/failure_message/failed_stage`; no transcript/prompt/secrets in response/logs. |

## Matrix: Export Identity, Provenance Freeze, and Download URL TTL

| test_id | priority | endpoint/method | fixtures | request | expected_status | assertions (+ audit/idempotency notes) |
| --- | --- | --- | --- | --- | --- | --- |
| `EXP_001` | P0 | `POST /jobs/{jobId}/exports` | `auth_editor_a`, `export_request_valid` | `{"instruction_version_id":"iv-10","format":"PDF"}` | `202` | `identity_key` computed from `instruction_version_id+format+screenshot_set_hash`; state starts `REQUESTED`. |
| `EXP_002` | P0 | `POST /jobs/{jobId}/exports` | `auth_editor_a`, `export_request_same_identity` | Replay same identity tuple | `200` | Same `export_id`; no duplicate export/workflow; duplicate business audit event suppressed. |
| `EXP_003` | P0 | `POST /jobs/{jobId}/exports` | `auth_editor_a`, `db_snapshot` | Invalid version or format | `400` | `code=EXPORT_REQUEST_INVALID`; no export record. |
| `EXP_004` | P0 | `POST /jobs/{jobId}/exports` | `auth_editor_a`, `export_request_valid` | Valid export request | `202` | Provenance includes `instruction_version_id,screenshot_set_hash,anchors,active_asset_id,rendered_asset_id`; snapshot/model/prompt refs are IDs only. |
| `EXPG_001` | P0 | `GET /exports/{exportId}` | `auth_editor_a` | Query each lifecycle state fixture | `200` | `status ∈ {REQUESTED,RUNNING,SUCCEEDED,FAILED}` only. |
| `EXPG_002` | P0 | `GET /exports/{exportId}` | `auth_editor_a`, `export_record_succeeded` | Query succeeded export repeatedly | `200` | `provenance_frozen_at` set; provenance + identity fields remain byte-identical across reads. |
| `EXPG_003` | P0 | `GET /exports/{exportId}` | `auth_editor_a`, `export_record_succeeded`, `settings_export_ttl`, `clock_freeze` | Query succeeded export | `200` | `download_url` present and scoped; `download_url_expires_at` present; expiry delta <= configured TTL window. |
| `EXPG_004` | P0 | `GET /exports/{exportId}` | `auth_editor_a` | Query non-succeeded export | `200` | `download_url` absent/unusable before `SUCCEEDED`. |

## Matrix: Anchor/Asset Lifecycle Determinism (P0)

| test_id | priority | endpoint/method | fixtures | request | expected_status | assertions (+ audit/idempotency notes) |
| --- | --- | --- | --- | --- | --- | --- |
| `ANC_001` | P0 | `POST /instructions/{instructionId}/anchors` | `auth_editor_a`, `instruction_vn` | `{"instruction_version_id":"iv-10","addressing":{"address_type":"block_id","block_id":"b-12"}}` | `201` | Anchor stores addressing type/value and strategy metadata. |
| `ANC_002` | P0 | `POST /instructions/{instructionId}/anchors` | `auth_editor_a`, `instruction_vn` | `{"instruction_version_id":"iv-10","addressing":{"address_type":"char_range","char_range":{"start_offset":100,"end_offset":180}}}` | `201` | Anchor stores exact `char_range` fallback address. |
| `ANL_001` | P0 | `GET /instructions/{instructionId}/anchors` | `auth_editor_a`, `anchor_block_id`, `anchor_char_range` | `?instruction_version_id=iv-10` | `200` | Returns only anchors bound to requested instruction version. |
| `ANL_002` | P0 | `GET /instructions/{instructionId}/anchors` | `auth_editor_a`, `anchor_with_asset_chain` | Default query (`include_deleted_assets=false`) | `200` | Deleted assets excluded from active selection; active asset stable. |
| `ANG_001` | P0 | `GET /anchors/{anchorId}` | `auth_editor_a`, `anchor_block_id` | `?target_instruction_version_id=iv-11` | `200` | `resolution.resolution_state` in `retain|remap|unresolved`; trace metadata links source/target versions. |
| `ANR_001` | P0 | `POST /anchors/{anchorId}/replace` | `auth_editor_a`, `anchor_with_asset_chain` | Valid replacement extraction payload | `202` | New asset version created; `active_asset_id` updates; `previous_asset_id` links prior active. |
| `ANR_002` | P0 | `POST /anchors/{anchorId}/replace` | `auth_editor_a`, `anchor_with_asset_chain`, `db_snapshot` | Replay same canonical extraction key/idempotency key | `200` | No new asset version; deterministic idempotent replay. |
| `AND_001` | P0 | `DELETE /anchors/{anchorId}/assets/{assetId}` | `auth_editor_a`, `anchor_with_asset_chain` | Delete current active asset | `200` | Fallback is deterministic: previous valid version else `null`; deleted asset remains historical. |
| `ANN_001` | P0 | `POST /anchors/{anchorId}/annotations` | `auth_editor_a`, `anchor_with_asset_chain`, `annotation_ops_normalized` | Valid ops list | `200` | Deterministic `ops_hash -> rendered_asset_id`; updates active rendered asset. |
| `ANN_002` | P0 | `POST /anchors/{anchorId}/annotations` | `auth_editor_a`, `annotation_ops_normalized`, `db_snapshot` | Replay same base asset + normalized ops | `200` | Same `rendered_asset_id`; no duplicate render artifact. |
| `ANN_003` | P0 | `POST /anchors/{anchorId}/annotations` | `auth_editor_a`, `annotation_ops_normalized`, `render_fail_injection`, `db_snapshot` | Inject render failure | `500` (injected) | Prior active annotation state unchanged; no partial asset/anchor mutation. |

## Matrix: Cross-Cutting Security and Audit Assertions

| test_id | priority | endpoint/method | fixtures | request | expected_status | assertions (+ audit/idempotency notes) |
| --- | --- | --- | --- | --- | --- | --- |
| `X_001` | P0 | Multi-endpoint (`/jobs/*`, `/instructions/*`, `/exports/*`, `/anchors/*`) | `auth_editor_b` | Unauthorized and nonexistent resource probes | `404` | Uniform no-leak behavior (`RESOURCE_NOT_FOUND`) across endpoints. |
| `X_002` | P0 | Multi-endpoint failure/replay paths | `log_capture` | Execute representative error + replay cases | endpoint-specific | No secrets, raw transcript, or raw prompt content in logs. |
| `X_003` | P0 | Audit-producing transitions + export/regenerate flows | `audit_reader` | Execute one success + one replay per flow | endpoint-specific | Required audit fields present; duplicate idempotent business events suppressed. |

## Execution Notes

- Run `P0` first as release gate (`pytest -m "p0 and high_risk"`).
- Keep deterministic seeds for timestamp- and hash-based tests.
- For injected-failure atomicity/rollback tests, assert non-2xx and state invariants instead of strict contract code.
- Pair endpoint tests with direct repository assertions for idempotency key uniqueness and immutable provenance checks.
