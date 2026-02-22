# Focused Delta List: PRD vs Epics vs OpenAPI (Step 4 Traceability Pass)

**Date:** 2026-02-22  
**Project:** Howera  
**Status:** Reconciled for `FR-033..FR-045` at contract level (OpenAPI aligned)

## Scope

Compared sources:
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`

Purpose:
- Re-validate PRD and Epics FR parity
- Validate OpenAPI contract alignment after step 2 + step 3
- Identify any remaining contract-level deltas before IR re-run

## Snapshot

- PRD FR scope: `FR-001..FR-045`
- Epics FR scope: `FR-001..FR-045`
- Set comparison result: no FR missing in either PRD or Epics
- OpenAPI now includes expanded paths/schemas and tightened semantics for `FR-033..FR-045`

Evidence:
- PRD FR list includes `FR-033..FR-045`: `_bmad-output/planning-artifacts/prd.md:324`
- Epics FR list includes `FR-033..FR-045`: `_bmad-output/planning-artifacts/epics.md:55`

## FR Matrix (FR-033..FR-045)

| FR | PRD | Epics | OpenAPI | Evidence |
| --- | --- | --- | --- | --- |
| FR-033 Replace screenshot asset | Present | Present | Present | `POST /anchors/{anchorId}/replace` at `spec/api/openapi.yaml:1646`, `ScreenshotReplaceRequest` at `spec/api/openapi.yaml:753` |
| FR-034 Soft-delete screenshot asset | Present | Present | Present | `DELETE /anchors/{anchorId}/assets/{assetId}` at `spec/api/openapi.yaml:1691`, fallback response at `spec/api/openapi.yaml:775` |
| FR-035 Custom image upload + attach | Present | Present | Present | Upload + confirm + attach paths at `spec/api/openapi.yaml:1720`, `spec/api/openapi.yaml:1744`, `spec/api/openapi.yaml:1773` |
| FR-036 Annotation operation log + rendered artifact | Present | Present | Present | `AnnotationOperation` at `spec/api/openapi.yaml:857`, annotate endpoint at `spec/api/openapi.yaml:1797`, `ops_hash` response at `spec/api/openapi.yaml:885` |
| FR-037 Anchor create/retrieve with block strategy | Present | Present | Present | Anchor create/list/get at `spec/api/openapi.yaml:1569`, `spec/api/openapi.yaml:1623`; addressing schema at `spec/api/openapi.yaml:595` |
| FR-038 Anchor stability across instruction versions | Present | Present | Present | `AnchorResolution` (`retain/remap/unresolved`) at `spec/api/openapi.yaml:610`; target-version query at `spec/api/openapi.yaml:1634` |
| FR-039 Export requires instruction version | Present | Present | Present | `CreateExportRequest` requires `instruction_version_id` at `spec/api/openapi.yaml:931`; export request path at `spec/api/openapi.yaml:1836` |
| FR-040 Export reproducibility tuple | Present | Present | Present | `ExportProvenance` with `instruction_version_id`, `screenshot_set_hash`, anchor bindings at `spec/api/openapi.yaml:954`; identity key in `Export` at `spec/api/openapi.yaml:978` |
| FR-041 Cancel running job | Present | Present | Present | `POST /jobs/{jobId}/cancel` at `spec/api/openapi.yaml:1196` |
| FR-042 Retry failed job from checkpoint | Present | Present | Present | `POST /jobs/{jobId}/retry` at `spec/api/openapi.yaml:1229`, retry metadata in `RetryJobResponse` at `spec/api/openapi.yaml:506` |
| FR-043 Model profile selection policy | Present | Present | Present | `RetryJobRequest.model_profile` at `spec/api/openapi.yaml:499`; regenerate model profile fields at `spec/api/openapi.yaml:388` |
| FR-044 Prompt template/params linkage | Present | Present | Present | Regenerate prompt refs at `spec/api/openapi.yaml:388`; export prompt refs at `spec/api/openapi.yaml:954` |
| FR-045 Instruction validation status | Present | Present | Present | Instruction validation fields at `spec/api/openapi.yaml:326` |

## Semantics Alignment Checklist

### Job intake, FSM, callback, retry

- Confirm-upload idempotency + conflict semantics: aligned
  - `POST /jobs/{jobId}/confirm-upload` descriptions/responses at `spec/api/openapi.yaml:1108`
  - `VIDEO_URI_CONFLICT` schema at `spec/api/openapi.yaml:92`
- Invalid FSM transition error semantics (`409`, explicit code, current/attempted): aligned
  - `FsmTransitionError` at `spec/api/openapi.yaml:80`
- Callback idempotency keyed by `(job_id, event_id)`, replay behavior, out-of-order policy: aligned
  - Callback semantics in description at `spec/api/openapi.yaml:1918`
  - Replay response schema at `spec/api/openapi.yaml:555`
  - `EVENT_ID_PAYLOAD_MISMATCH` and `CALLBACK_OUT_OF_ORDER` schemas at `spec/api/openapi.yaml:172`, `spec/api/openapi.yaml:151`
- Transactional consistency + merge-safe manifest policy: aligned at contract semantics level
  - Callback description at `spec/api/openapi.yaml:1929`
- Retry state-gating + idempotent dispatch + resume/checkpoint/model profile fields: aligned
  - Retry endpoint at `spec/api/openapi.yaml:1229`
  - Retry payload/response at `spec/api/openapi.yaml:499`, `spec/api/openapi.yaml:506`

### Transcript and instruction lifecycle

- Transcript allowed states + pagination + no-existence-leak policy: aligned
  - Transcript endpoint at `spec/api/openapi.yaml:1296`
  - Paginated response schema `TranscriptPage` at `spec/api/openapi.yaml:571`
- Instruction GET required fields + latest/versioned retrieval semantics: aligned
  - Instruction schema at `spec/api/openapi.yaml:326`
  - Version query behavior at `spec/api/openapi.yaml:1349`
- Instruction PUT optimistic concurrency (`base_version`) + `409 VERSION_CONFLICT`: aligned
  - `UpdateInstructionRequest` at `spec/api/openapi.yaml:365`
  - `VersionConflictError` at `spec/api/openapi.yaml:110`
- Validation persisted fields and sanitized constraints: aligned at schema+description level
  - Validation fields at `spec/api/openapi.yaml:326`
- Regenerate selection addressing + idempotency + provenance + success-version linkage: aligned
  - `RegenerateRequest` and `RegenerateTask` at `spec/api/openapi.yaml:388`, `spec/api/openapi.yaml:430`
  - Regenerate endpoint semantics at `spec/api/openapi.yaml:1420`

### Screenshot/anchor lifecycle and export determinism

- Async extraction/replace + dedupe policy: aligned
  - Extract endpoint at `spec/api/openapi.yaml:1505`
  - Replace endpoint at `spec/api/openapi.yaml:1646`
- Asset version graph (`active_asset_id`, `previous_asset_id`) + soft-delete fallback surface: aligned
  - `ScreenshotAsset` at `spec/api/openapi.yaml:625`
  - `ScreenshotAnchor` at `spec/api/openapi.yaml:668`
  - Soft-delete response at `spec/api/openapi.yaml:775`
- Custom upload signed flow + MIME/size/checksum/dimensions capture: aligned
  - Upload schemas at `spec/api/openapi.yaml:786`, `spec/api/openapi.yaml:801`, `spec/api/openapi.yaml:820`
- Annotation op schema + deterministic render key (`ops_hash`) + idempotent semantics: aligned
  - Op schemas at `spec/api/openapi.yaml:857`, `spec/api/openapi.yaml:885`
- Export identity key/idempotency + provenance + export FSM + URL policy + audit taxonomy: aligned
  - `ExportStatus` FSM at `spec/api/openapi.yaml:904`
  - Identity key and provenance in schemas at `spec/api/openapi.yaml:931`, `spec/api/openapi.yaml:954`, `spec/api/openapi.yaml:978`
  - Export audit event types at `spec/api/openapi.yaml:908`
  - Export endpoint semantics at `spec/api/openapi.yaml:1836`, `spec/api/openapi.yaml:1889`

## Residual Notes (Non-Blocking for Contract Alignment)

1. Some guarantees are intentionally behavioral (transaction atomicity, duplicate write suppression, audit emission suppression) and are documented in endpoint descriptions rather than fully schema-enforceable.
2. These behavioral guarantees should be verified in implementation tests and readiness checks, not by schema validation alone.

## Step-4 Conclusion

Contract-level deltas identified earlier for `FR-033..FR-045` and associated semantics are reconciled in OpenAPI.

Recommended next step:
- Re-run `/bmad-bmm-check-implementation-readiness` against updated artifacts.
