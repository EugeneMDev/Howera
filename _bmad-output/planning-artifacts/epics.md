---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - spec/sas.md
  - spec/acceptance/tasks_codex_v1.md
---

# Howera - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Howera, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-001: Authenticated user can create a project.
FR-002: Authenticated user can list and retrieve only their own projects.
FR-003: Authenticated user can create a job under a project they own.
FR-004: Authenticated user can retrieve status for a job they own.
FR-005: System validates callback secret for internal workflow callback endpoint.
FR-006: User can confirm upload for a job by submitting `video_uri`.
FR-007: System can transition job state only via allowed FSM transitions.
FR-008: System must prevent mutation of terminal states (`FAILED`, `CANCELLED`, `DONE`).
FR-009: User can trigger workflow execution for an uploaded job.
FR-010: System stores and updates artifact manifest as lifecycle progresses.
FR-011: System preserves checkpoint states (`AUDIO_READY`, `TRANSCRIPT_READY`, `DRAFT_READY`) for resumability.
FR-012: Internal callback can submit `event_id`, `status`, and `occurred_at`.
FR-013: System detects duplicate `event_id` and treats duplicate callback as no-op.
FR-014: Callback status updates must be rejected when violating FSM transition rules.
FR-015: Callback processing can attach artifact updates consistently with state changes.
FR-016: Callback processing can record failure metadata (`failure_code`, `failure_message`, `failed_stage`).
FR-017: User can retrieve transcript segments for a job.
FR-018: User can retrieve instruction content by instruction ID.
FR-019: User can update instruction markdown and receive updated instruction version metadata.
FR-020: User can request targeted regeneration on instruction selection range.
FR-021: User can query regenerate task status until completion/failure.
FR-022: User can request screenshot extraction for a job at `timestamp_ms`.
FR-023: Screenshot extraction accepts optional alignment parameters (`offset_ms`, strategy, format) per API contract.
FR-024: System returns screenshot anchor details including `asset_id`, `image_uri`, and dimensions.
FR-025: User can request export generation for supported formats (`PDF`, `MD_ZIP`).
FR-026: System provides export status retrieval by export ID.
FR-027: System returns downloadable URL for completed exports.
FR-028: System associates export artifacts with originating job manifest/history.
FR-029: System records auditable events for status transitions.
FR-030: System records auditable events for export requests/completions.
FR-031: System records auditable events for regenerate requests.
FR-032: System avoids storing secrets or raw transcript text in logs.
FR-033: User can replace an existing screenshot asset linked to an anchor by requesting a new extraction with updated `timestamp_ms` and/or `offset_ms`.
FR-034: User can delete (soft-delete) a screenshot asset and unlink it from its anchor without mutating immutable raw artifacts.
FR-035: User can upload a custom image file and attach it to an existing or new screenshot anchor.
FR-036: User can create and update screenshot annotations (for example blur, arrow, marker, pencil) stored as an operation log and associated rendered image artifact.
FR-037: System supports creation and retrieval of screenshot anchors linked to instruction version blocks (`block_id`) or approved fallback strategy.
FR-038: System ensures anchor stability across instruction version updates according to defined anchor persistence policy.
FR-039: Export request must reference a specific instruction version identifier.
FR-040: System guarantees export reproducibility by associating each export artifact with instruction version ID, linked screenshot asset versions, and generation timestamp.
FR-041: User can cancel a running job when allowed by FSM transition rules.
FR-042: User can retry a failed job from the latest valid checkpoint state without duplicating prior completed stages.
FR-043: System supports selection of model profile (for example cloud or local provider) per environment or job configuration according to allowed policies.
FR-044: System stores and links system prompt template and prompt parameters used during draft generation to ensure reproducibility and auditability.
FR-045: System validates generated instruction markdown against a minimal structural schema (for example step structure and headings) and records validation status.

### NonFunctional Requirements

NFR-001: System should target draft generation completion under 10 minutes for a 60-minute video in baseline target environment.
NFR-002: Job status retrieval endpoints should return within interactive API latency expectations for normal load.
NFR-003: Callback handling should complete quickly enough to avoid orchestrator timeout/retry cascades.
NFR-004: All write operations require authenticated identity validation.
NFR-005: Internal callback endpoint requires shared-secret verification.
NFR-006: Signed URLs for storage access must be time-limited.
NFR-007: Secrets must be sourced from environment/secret management and never logged.
NFR-008: Asynchronous workflow architecture must support horizontal worker/orchestrator scaling.
NFR-009: Design must permit provider replacement and deployment-mode evolution without business-domain rewrites.
NFR-010: Any user-facing web surfaces in scope should target WCAG-aligned accessibility baseline as practical for MVP.
NFR-011: API and orchestrator integration must use stable contract payloads for run/callback flows.
NFR-012: STT/LLM integrations must pass through adapters with normalized internal outputs.
NFR-013: CI quality gates must include lint/test/check and golden-path validation in mock mode.

### Additional Requirements

- No explicit starter template requirement is specified in `spec/sas.md`; treat project initialization as brownfield-aligned setup.
- Workflow orchestration must follow `Upload -> Audio Extraction -> STT -> LLM Generation -> Human Editing -> Export` with async processing via n8n.
- Provider abstraction is mandatory; OpenAI and local providers must be interchangeable behind adapter boundaries.
- Model provider selection is global per environment/pipeline configuration, not user-configurable at runtime.
- Signed URLs must be used for storage upload/download interactions.
- Job lifecycle state model must preserve deterministic transitions and include failure handling (`FAILED`) and completion (`DONE`).
- Raw artifacts are immutable; transcripts, instruction versions, screenshot assets, and exports are persisted as linked artifacts.
- Metadata model must support jobs, transcript segments, instruction versions, screenshot anchors/assets, model configs, and audit logs.
- Integration contracts should preserve run/callback boundaries and include STT/LLM generation and regenerate flows.
- Retry behavior must use bounded retries with exponential backoff; export operations must be idempotent.
- Security baseline includes authenticated access (role `editor`), TLS in transit, encryption at rest, centralized secret management, and audit logging.
- Deployment design must remain phase-compatible: v1 cloud-first, v2 hybrid local-provider support, v3 full on-prem with air-gapped readiness.
- Observability baseline requires correlation IDs, stage duration metrics, failure rates, and queue/storage/model alerts.
- Testing baseline includes unit, integration, adapter contract tests, load testing, and security testing.
- From Codex Task Pack constraints: `spec/` is read-only, one task per logical change, no business logic in route functions, and external integrations must use adapters.

### FR Coverage Map

FR-001: Epic 1 - Project creation access
FR-002: Epic 1 - Owned project visibility boundaries
FR-003: Epic 1 - Job creation within owned project
FR-004: Epic 1 - Owned job status visibility
FR-005: Epic 1 - Internal callback secret validation
FR-006: Epic 2 - Upload confirmation with `video_uri`
FR-007: Epic 3 - FSM-enforced status transitions
FR-008: Epic 3 - Terminal state immutability
FR-009: Epic 2 - Workflow run initiation
FR-010: Epic 3 - Artifact manifest lifecycle updates
FR-011: Epic 3 - Checkpoint preservation for resumability
FR-012: Epic 3 - Callback event payload contract
FR-013: Epic 3 - Duplicate callback idempotency
FR-014: Epic 3 - Rejection of invalid callback transitions
FR-015: Epic 3 - Callback artifact updates synchronized with state
FR-016: Epic 3 - Callback failure metadata persistence
FR-017: Epic 4 - Transcript segment retrieval
FR-018: Epic 4 - Instruction retrieval by ID
FR-019: Epic 4 - Instruction update and version metadata
FR-020: Epic 4 - Targeted regenerate request
FR-021: Epic 4 - Regenerate task polling
FR-022: Epic 5 - Screenshot extraction at timestamp
FR-023: Epic 5 - Screenshot alignment parameter support
FR-024: Epic 5 - Screenshot anchor response metadata
FR-025: Epic 6 - Export request creation
FR-026: Epic 6 - Export status retrieval
FR-027: Epic 6 - Export download URL retrieval
FR-028: Epic 6 - Export artifact linkage to job manifest/history
FR-029: Epic 3 - Auditable status transition events
FR-030: Epic 6 - Auditable export events
FR-031: Epic 4 - Auditable regenerate events
FR-032: Epic 1 - Secure logging boundary (no secrets/raw transcript logging)
FR-033: Epic 5 - Screenshot asset replacement
FR-034: Epic 5 - Screenshot soft-delete and unlink
FR-035: Epic 5 - Custom image upload attachment to anchor
FR-036: Epic 5 - Annotation operation log and rendered artifact
FR-037: Epic 5 - Anchor create/retrieve with `block_id` strategy
FR-038: Epic 5 - Anchor stability across instruction versions
FR-039: Epic 6 - Export bound to specific instruction version
FR-040: Epic 6 - Reproducible export provenance tuple
FR-041: Epic 3 - Cancel running job under FSM rules
FR-042: Epic 3 - Retry failed job from checkpoint safely
FR-043: Epic 3 - Model profile selection under allowed policy
FR-044: Epic 6 - Prompt template/parameters linkage for reproducibility
FR-045: Epic 4 - Instruction markdown structural validation status

## Epic List

### Epic 1: Workspace Access and Secure Ownership Baseline
Editors can authenticate and operate only within authorized ownership boundaries while enforcing secure logging constraints.
**FRs covered:** FR-001, FR-002, FR-003, FR-004, FR-005, FR-032

### Epic 2: Job Intake and Workflow Start
Editors can confirm uploads and initiate workflow execution reliably.
**FRs covered:** FR-006, FR-009

### Epic 3: Deterministic State Engine and Recovery
Editors get predictable lifecycle behavior with FSM enforcement, callback integrity, auditable transitions, and checkpoint-based recovery.
**FRs covered:** FR-007, FR-008, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-029, FR-041, FR-042, FR-043

### Epic 4: Transcript-Driven Authoring, Regeneration, and Quality Validation
Editors can author from transcript context, regenerate targeted content, and maintain structurally valid instructions with regenerate auditability.
**FRs covered:** FR-017, FR-018, FR-019, FR-020, FR-021, FR-031, FR-045

### Epic 5: Screenshot and Anchor Lifecycle Management
Editors can extract, replace, delete, upload, annotate, and persist screenshot anchors/assets across instruction versions.
**FRs covered:** FR-022, FR-023, FR-024, FR-033, FR-034, FR-035, FR-036, FR-037, FR-038

### Epic 6: Deterministic Export and Provenance
Editors can produce reproducible exports tied to exact instruction and screenshot asset versions with complete export audit trace.
**FRs covered:** FR-025, FR-026, FR-027, FR-028, FR-030, FR-039, FR-040, FR-044

## Epic 1: Workspace Access and Secure Ownership Baseline

Editors can authenticate and operate only within authorized ownership boundaries while enforcing secure logging constraints.

### Story 1.1: Authenticate API Requests as Editor

As an editor,
I want authenticated API requests to resolve my identity,
So that protected operations are executed only for valid users.

**Acceptance Criteria:**

**Given** a request to a protected write endpoint without a valid bearer token
**When** the request is processed
**Then** the API returns `401 Unauthorized`
**And** no domain write operation is executed.

**Given** a request with a valid token containing editor identity
**When** the request is processed
**Then** the API resolves `user_id` into request context
**And** downstream handlers can enforce ownership checks.

### Story 1.2: Create and Read Owned Projects

As an editor,
I want to create projects and read only my own projects,
So that my workspace is isolated from other users.

**Acceptance Criteria:**

**Given** an authenticated editor
**When** they create a project
**Then** the project is persisted with that editor as owner
**And** response fields match OpenAPI contract.

**Given** two editors with separate projects
**When** one editor lists or retrieves projects
**Then** only that editor's projects are returned
**And** cross-owner project access is denied.

### Story 1.3: Create Jobs in Owned Projects and Read Owned Job Status

As an editor,
I want to create jobs under my projects and read status for my own jobs,
So that I can manage processing safely within my workspace.

**Acceptance Criteria:**

**Given** an authenticated editor and owned project
**When** they create a job
**Then** the job is created under that project
**And** initial state is contract-compliant.

**Given** a job owned by another editor
**When** an editor requests its status
**Then** access is denied
**And** no job data is exposed.

### Story 1.4: Validate Internal Callback Secret

As a platform operator,
I want internal status callbacks to require a shared secret,
So that only trusted orchestrator calls can mutate internal status.

**Acceptance Criteria:**

**Given** an internal callback request without valid `X-Callback-Secret`
**When** the endpoint is invoked
**Then** the API rejects the request
**And** no status mutation is performed.

**Given** a callback with valid secret
**When** payload validation succeeds
**Then** the callback is accepted for domain processing
**And** the request follows normal FSM and idempotency processing.

### Story 1.5: Enforce Secure Logging Boundaries

As a security-conscious editor,
I want logs to exclude secrets and raw transcript payloads,
So that sensitive data is not leaked through observability systems.

**Acceptance Criteria:**

**Given** authenticated and callback flows with sensitive fields
**When** logs are emitted
**Then** secrets and raw transcript content are omitted or redacted
**And** correlation metadata remains available for debugging.

**Given** test scenarios covering auth and callback paths
**When** log output is inspected
**Then** no forbidden sensitive values appear
**And** the test suite fails on regression.

## Epic 2: Job Intake and Workflow Start

Editors can confirm uploads and initiate workflow execution reliably.

### Story 2.1: Confirm Job Upload with Video URI

As an editor,
I want to confirm a job upload by submitting `video_uri`,
So that the system can accept the job for processing.

**Acceptance Criteria:**

**Given** an authenticated editor with an owned eligible job and valid `video_uri`
**When** confirm-upload is requested
**Then** job transitions to `UPLOADED` via FSM
**And** `artifact_manifest.video_uri` is stored exactly as submitted
**And** the response matches the OpenAPI contract.

**Given** confirm-upload is called again with the same `video_uri`
**When** the request is processed
**Then** processing is idempotent
**And** no duplicate writes occur
**And** no additional state transitions occur.

**Given** confirm-upload is called with a different `video_uri` for the same job
**When** the request is processed
**Then** the API returns a contract-defined conflict error
**And** no mutation occurs.

### Story 2.2: Start Workflow Run for an Upload-Confirmed Job

As an editor,
I want to trigger processing for my upload-confirmed job,
So that draft generation begins asynchronously.

**Acceptance Criteria:**

**Given** an authenticated editor with an owned job in `UPLOADED` state
**When** `POST /jobs/{jobId}/run` is called
**Then** the API accepts the request
**And** exactly one workflow execution is dispatched to the orchestrator.

**Given** the job is not in `UPLOADED` state
**When** `POST /jobs/{jobId}/run` is called
**Then** the API returns a contract-defined error
**And** no dispatch occurs.

**Given** repeated run calls are made for the same eligible job
**When** requests are processed
**Then** the endpoint behaves idempotently
**And** duplicate orchestrator executions are not created.

**Given** a dispatch is performed
**When** the orchestrator payload is built
**Then** it includes `job_id`, `project_id`, `video_uri`, and `callback_url`.

**Given** orchestrator dispatch fails
**When** failure is detected
**Then** job state is not advanced
**And** a contract-defined upstream error is returned.

**Given** run dispatch and failure handling paths execute
**When** logs are emitted
**Then** no secrets or raw transcript content are logged.

## Epic 3: Deterministic State Engine and Recovery

Editors get predictable lifecycle behavior with FSM enforcement, callback integrity, auditable transitions, and checkpoint-based recovery.

### Story 3.1: Enforce FSM Transition Rules and Lifecycle Invariants

As an editor,
I want all job status changes validated by FSM,
So that lifecycle behavior remains deterministic and safe.

**Acceptance Criteria:**

**Given** a status transition request from `current_status` to `attempted_status` that is not allowed by FSM
**When** transition validation runs
**Then** the API returns `409` with `error_code=FSM_TRANSITION_INVALID`
**And** the error payload includes `current_status`, `attempted_status`, and `allowed_next_statuses`
**And** no mutation is persisted.

**Given** a transition request for terminal state mutation (`FAILED`, `CANCELLED`, `DONE` to any new status)
**When** validation runs
**Then** the API returns `409` with `error_code=FSM_TERMINAL_IMMUTABLE`
**And** no mutation is persisted.

### Story 3.2: Validate Callback Contract, Idempotency, and Ordering Policy

As a platform operator,
I want callback processing to validate payload and reject duplicates safely,
So that asynchronous updates are replay-safe.

**Acceptance Criteria:**

**Given** callback payload with `job_id`, `event_id`, `status`, and `occurred_at`
**When** first accepted
**Then** idempotency record is stored with unique key `(job_id, event_id)`
**And** callback processing proceeds once.

**Given** same `(job_id, event_id)` and same payload hash is replayed
**When** received again
**Then** API returns contract-defined replay success (`200` no-op)
**And** `replayed=true` is returned (or equivalent contract field)
**And** no state or artifact writes are repeated.

**Given** same `(job_id, event_id)` but different payload content
**When** received
**Then** API returns `409` with `error_code=EVENT_ID_PAYLOAD_MISMATCH`
**And** no mutation is persisted.

**Given** callback `occurred_at` is older than latest applied event and implies backward or non-monotonic transition
**When** evaluated
**Then** API returns `409` with `error_code=CALLBACK_OUT_OF_ORDER`
**And** response includes `latest_applied_occurred_at`, `current_status`, and `attempted_status`
**And** no mutation is persisted.

### Story 3.3: Transactional Consistency for State, Manifest, and Failure Metadata

As an operator,
I want callback side effects to be state-consistent,
So that artifact records and status remain aligned.

**Acceptance Criteria:**

**Given** callback mutation includes status, manifest updates, and optional failure metadata
**When** persisted
**Then** state change, `artifact_manifest` merge, and failure fields are committed in one transaction
**And** any write failure rolls back all three.

**Given** manifest update is applied
**When** merge executes
**Then** update is merge-safe (keyed merge with no destructive overwrite of unrelated keys)
**And** immutable raw artifact entries are never replaced or deleted implicitly.

### Story 3.4: Emit Auditable Status Transition Events

As a compliance stakeholder,
I want status transitions to produce auditable events,
So that job lifecycle decisions are traceable.

**Acceptance Criteria:**

**Given** any accepted state transition
**When** audit event is recorded
**Then** event includes required fields: `event_type`, `job_id`, `project_id`, `actor_type`, `prev_status`, `new_status`, `occurred_at`, `recorded_at`, `correlation_id`
**And** event payload excludes secrets and raw transcript content.

**Given** duplicate callback replay (no-op)
**When** processed
**Then** no duplicate transition audit event is emitted.

### Story 3.5: Cancel Running Job via FSM-Governed Rules

As an editor,
I want to cancel an in-flight job when allowed,
So that I can stop unwanted processing safely.

**Acceptance Criteria:**

**Given** owned job in cancellable state
**When** cancel is requested
**Then** transition to `CANCELLED` is applied via FSM
**And** audit event is emitted with required fields.

**Given** job is non-cancellable
**When** cancel is requested
**Then** API returns `409` with `error_code=FSM_TRANSITION_INVALID`
**And** response includes `current_status` and `attempted_status=CANCELLED`
**And** no mutation is persisted.

### Story 3.6: Retry Failed Job from Checkpoint with Policy-Bound Model Profile

As an editor,
I want to retry a failed job from its latest valid checkpoint under allowed model policy,
So that recovery is efficient and controlled.

**Acceptance Criteria:**

**Given** retry request
**When** validation runs
**Then** retry is allowed only from `FAILED`
**And** request is rejected otherwise with `409` and `error_code=RETRY_NOT_ALLOWED_STATE`.

**Given** job is already running, dispatched, or in-progress
**When** retry is requested
**Then** API returns `409` with `error_code=JOB_ALREADY_RUNNING`
**And** no new dispatch occurs.

**Given** valid retry
**When** accepted
**Then** `resume_from_status` and checkpoint reference are resolved and persisted
**And** model profile selection is policy-validated and recorded with retry metadata.

**Given** repeated identical retry request
**When** processed
**Then** retry dispatch is idempotent (no duplicate orchestrator execution)
**And** previously created dispatch reference is returned.

**Given** dispatch payload is built
**When** sent to orchestrator
**Then** it includes `job_id`, `project_id`, `video_uri`, `callback_url`, `resume_from_status`, `checkpoint_ref`, and `model_profile`.

**Given** orchestrator dispatch fails
**When** failure occurs
**Then** job state is not advanced
**And** API returns contract-defined upstream error (for example `502` with `error_code=ORCHESTRATOR_DISPATCH_FAILED`).

## Epic 4: Transcript-Driven Authoring, Regeneration, and Quality Validation

Editors can author from transcript context, regenerate targeted content, and maintain structurally valid instructions with regenerate auditability.

### Story 4.1: Retrieve Transcript Segments for Job

As an editor,
I want transcript segments for my job,
So that I can ground edits and regeneration on source timing and text.

**Acceptance Criteria:**

**Given** an authenticated editor requesting transcript for an owned job in allowed states (`TRANSCRIPT_READY`, `GENERATING`, `DRAFT_READY`, `EDITING`, `EXPORTING`, `DONE`, `FAILED`)
**When** transcript retrieval is called
**Then** API returns contract-compliant transcript segments ordered by `start_ms`
**And** applies pagination and size policy (`limit`, `cursor` or `offset`, and contract-defined max page size).

**Given** transcript retrieval is requested for non-owned or nonexistent resource
**When** authorization and resource checks run
**Then** API uses no-existence-leak policy (`404` for both cases)
**And** no ownership details are exposed.

**Given** job is in a state where transcript is not yet available
**When** retrieval is requested
**Then** API returns contract-defined availability error
**And** response and logs exclude raw transcript beyond explicitly returned segment payload.

### Story 4.2: Retrieve Instruction Content by ID

As an editor,
I want to fetch instruction content by instruction ID,
So that I can review the current editable draft or a specific version.

**Acceptance Criteria:**

**Given** an authenticated editor requesting an owned instruction
**When** retrieval succeeds
**Then** response includes required fields: `instruction_id`, `job_id`, `version`, `updated_at`, `validation_status`, and markdown content.

**Given** retrieval mode is latest by default
**When** no version is specified
**Then** API returns latest instruction version.

**Given** retrieval mode requests a specific version (if supported by contract)
**When** version exists
**Then** API returns that exact version payload
**And** indicates version identity unambiguously.

**Given** resource is unauthorized or nonexistent
**When** retrieval is requested
**Then** no-existence-leak policy is applied (`404`).

### Story 4.3: Update Instruction Markdown with Versioning and Concurrency Control

As an editor,
I want to save updated instruction markdown with optimistic concurrency,
So that concurrent edits do not silently overwrite each other.

**Acceptance Criteria:**

**Given** update payload includes `base_version` and markdown for an owned instruction
**When** `base_version` matches current persisted version
**Then** update is accepted
**And** a new instruction version is created
**And** response returns new version metadata (`instruction_id`, `job_id`, `version`, `updated_at`, `validation_status`).

**Given** `base_version` is stale
**When** update is attempted
**Then** API returns `409` with `error_code=VERSION_CONFLICT`
**And** no mutation occurs.

### Story 4.4: Structural Validation on Create and Update with Persisted Result

As an editor,
I want structural validation to run on instruction create and update,
So that instruction quality status is explicit and traceable.

**Acceptance Criteria:**

**Given** an instruction version is created (generation, regeneration, or save)
**When** persistence completes
**Then** structural validation runs automatically on create and on update.

**Given** validation completes
**When** result is stored
**Then** persisted validation fields include `validation_status` (`PASS` or `FAIL`), `errors[]`, `validated_at`, and `validator_version`.

**Given** validation fails
**When** errors are recorded
**Then** `errors[]` contains schema and structure diagnostics only
**And** excludes transcript, prompt content, and secrets from persisted errors and logs.

### Story 4.5: Request Targeted Regeneration with Idempotency and Provenance

As an editor,
I want targeted regeneration with deduplication and provenance,
So that partial regeneration is reliable, traceable, and reproducible.

**Acceptance Criteria:**

**Given** regenerate request targets an owned instruction
**When** selection is submitted
**Then** selection addressing is validated as either `block_id` or contract-defined text offsets
**And** invalid selection returns contract-defined validation error.

**Given** regenerate request contains `client_request_id` (or dedupe key per policy)
**When** duplicate request is received
**Then** endpoint is idempotent
**And** existing task reference is returned without creating duplicate work.

**Given** regenerate request is accepted
**When** task is created
**Then** provenance is stored with `instruction_id`, `base_version`, `selection`, `requested_by`, `requested_at`, and where applicable `model_profile` and prompt template references.

**Given** regenerate task completes with `SUCCEEDED`
**When** output is persisted
**Then** a new instruction version is created
**And** validation is executed for that new version
**And** regenerate audit event is recorded.

### Story 4.6: Poll Regenerate Task Status with Sanitized Outcomes

As an editor,
I want to poll regenerate task status,
So that I can detect completion or failure and fetch safe outcome metadata.

**Acceptance Criteria:**

**Given** owned regenerate task ID
**When** task is polled
**Then** API returns contract-defined state and progress metadata.

**Given** task state is `SUCCEEDED`
**When** status response is returned
**Then** response includes reference to the new instruction version (`instruction_id`, `version`, or contract equivalent).

**Given** task state is `FAILED`
**When** status response is returned
**Then** response includes sanitized failure fields only (`failure_code`, safe message, `failed_stage` if applicable)
**And** excludes secrets, raw transcript, and prompt content.

**Given** task ID is unknown or unauthorized
**When** status is polled
**Then** no-existence-leak policy is applied (`404`).

## Epic 5: Screenshot and Anchor Lifecycle Management

Editors can extract, replace, delete, upload, annotate, and persist screenshot anchors and assets across instruction versions.

### Story 5.1: Extract Screenshot with Alignment Parameters and Anchor Metadata

As an editor,
I want to request screenshot extraction at a timestamp with optional alignment parameters,
So that I can insert precise visual evidence into instructions.

**Acceptance Criteria:**

**Given** a valid extraction request with ownership-validated job and instruction context
**When** extraction is submitted
**Then** API accepts extraction as async (`202`) with `task_id` (preferred for FFmpeg latency)
**And** request stores an idempotency key or dedupe token (client key or canonical request key).

**Given** a duplicate extraction request (same canonical extraction key: `job_id + instruction_version + timestamp_ms + offset_ms + strategy + format`)
**When** processed
**Then** existing task or result is returned
**And** duplicate extraction work is not created.

**Given** extraction completes
**When** result is persisted
**Then** anchor and asset metadata includes `asset_id`, `image_uri`, dimensions, and extraction parameters
**And** ownership scope is enforced in retrieval.

### Story 5.2: Replace Existing Screenshot Asset for Anchor with Versioning

As an editor,
I want to replace an existing screenshot asset using updated timestamp and or offset,
So that anchor visuals can be corrected without losing traceability.

**Acceptance Criteria:**

**Given** valid replacement request for an owned anchor
**When** replacement is accepted
**Then** replacement is processed async (`202` with `task_id`)
**And** dedupe policy applies using canonical extraction key.

**Given** replacement completes
**When** versioning updates are persisted
**Then** anchor `active_asset_id` points to new asset version
**And** asset version increments
**And** `previous_asset_id` links to prior active asset.

**Given** replacement request matches current active canonical extraction key
**When** processed
**Then** operation is idempotent
**And** no new asset version is created.

### Story 5.3: Soft-Delete Screenshot Asset and Resolve Active Fallback

As an editor,
I want to soft-delete a screenshot asset and unlink it from active anchor use,
So that obsolete visuals are removed without mutating immutable raw artifacts.

**Acceptance Criteria:**

**Given** soft-delete request for owned asset linked to anchor
**When** deletion is applied
**Then** asset is marked soft-deleted
**And** deleted assets are excluded from active selection by default.

**Given** deleted asset equals anchor `active_asset_id`
**When** fallback policy executes
**Then** anchor `active_asset_id` resolves to previous valid version if available
**And** otherwise resolves to `null` (unbound state).

**Given** deleted assets exist
**When** history or audit query is requested
**Then** deleted versions remain queryable for history
**And** are clearly marked non-active.

### Story 5.4: Upload Custom Image via Signed URL and Confirm Attach

As an editor,
I want to upload a custom image and attach it to an anchor,
So that I can use manual visuals when extraction is insufficient.

**Acceptance Criteria:**

**Given** editor requests custom image upload
**When** API issues upload authorization
**Then** signed upload URL is returned with contract-defined expiry and constraints.

**Given** uploaded file confirm step is called
**When** validation runs
**Then** allowed MIME types are enforced: `image/png`, `image/jpeg`, `image/webp`
**And** size limits are enforced
**And** checksum and dimensions are captured and persisted.

**Given** file is SVG
**When** confirmation is attempted
**Then** upload is rejected unless contract-approved sanitizer flow exists
**And** default behavior disallows unsanitized SVG.

**Given** attach-to-anchor is requested
**When** confirmation succeeds
**Then** asset versioning and anchor `active_asset_id` update are applied transactionally.

### Story 5.5: Annotation Operations Schema and Deterministic Rendering

As an editor,
I want annotation edits stored as operation log and deterministic rendered output,
So that visual modifications are reproducible and auditable.

**Acceptance Criteria:**

**Given** annotation request on an owned base asset
**When** payload is validated
**Then** operations conform to schema (`op_type`, `geometry`, `style`, ordering)
**And** invalid operations are rejected with contract-defined validation error.

**Given** valid operation set
**When** render pipeline executes
**Then** deterministic rendering key `ops_hash` is computed from base asset and normalized operations
**And** rendered output maps to `rendered_asset_id` deterministically.

**Given** identical `ops_hash` is submitted again
**When** processed
**Then** operation is idempotent
**And** existing `rendered_asset_id` is returned without duplicate render.

**Given** render failure occurs
**When** transaction finalizes
**Then** prior active annotation state remains unchanged
**And** no partial anchor or asset mutation is persisted.

### Story 5.6: Anchor Addressing, Persistence Policy, and Cross-Version Traceability

As an editor,
I want anchors linked to instruction blocks to remain stable across version updates,
So that screenshot references stay predictable through edits.

**Acceptance Criteria:**

**Given** anchor create request
**When** addressing is validated
**Then** supported addressing types are `block_id` (primary) and `char_range` (fallback)
**And** stored anchor includes addressing type, value, and strategy metadata.

**Given** instruction version changes
**When** v1 anchor resolution policy runs
**Then** each anchor is classified as `retain`, `remap`, or `unresolved`
**And** trace metadata is stored linking source version to target version resolution result.

**Given** anchor and asset mutation operations (extract, replace, delete, upload, annotate)
**When** persistence occurs
**Then** anchor and asset updates are transactional and ownership-scoped
**And** no cross-owner mutation is possible.

**Given** export references anchored visuals
**When** export payload is built
**Then** export binds exact anchor and asset versions (not floating latest)
**And** provenance records those exact references.

## Epic 6: Deterministic Export and Provenance

Editors can produce reproducible exports tied to exact instruction and screenshot asset versions with complete export audit trace.

### Story 6.1: Create Export Request Bound to Exact Instruction Version

As an editor,
I want to request export for a specific instruction version,
So that generated artifacts are reproducible and non-ambiguous.

**Acceptance Criteria:**

**Given** an authenticated editor with owned job and explicit `instruction_version_id`
**When** export request is submitted with format
**Then** export identity key is computed as `instruction_version_id + format + screenshot_set_hash`
**And** request is idempotent on that identity key.

**Given** same identity key is requested again
**When** request is processed
**Then** existing `export_id` and current export state are returned
**And** no duplicate export record or workflow is created.

**Given** missing or invalid version or unsupported format
**When** request is submitted
**Then** API returns contract-defined validation error
**And** no export record is created.

### Story 6.2: Persist Complete Export Provenance and Snapshot References

As a compliance stakeholder,
I want each export to carry complete provenance,
So that output can be reproduced and audited.

**Acceptance Criteria:**

**Given** export request is accepted
**When** provenance is persisted
**Then** provenance includes `instruction_version_id`, `screenshot_set_hash`, active anchor set, `active_asset_id` per anchor, and `rendered_asset_id` where annotated.

**Given** instruction and screenshot content for export
**When** source references are resolved
**Then** export binds to stored instruction snapshot and immutable model and prompt references by IDs only
**And** raw prompt text is not stored in export provenance.

### Story 6.3: Execute Export FSM and Freeze Provenance on Success

As an editor,
I want export execution to follow deterministic lifecycle states,
So that retries and completion behavior are predictable.

**Acceptance Criteria:**

**Given** export lifecycle processing
**When** state transitions occur
**Then** export FSM is `REQUESTED -> RUNNING -> SUCCEEDED|FAILED`
**And** illegal transitions are rejected.

**Given** export reaches `SUCCEEDED`
**When** completion is persisted
**Then** provenance is frozen and immutable
**And** artifact linkage references frozen provenance and identity key.

**Given** duplicate execution trigger for same identity key
**When** processed
**Then** execution is idempotent
**And** duplicate artifacts are not created.

### Story 6.4: Retrieve Export Status by Export ID

As an editor,
I want to query export status by export ID,
So that I can track asynchronous export progress.

**Acceptance Criteria:**

**Given** owned `export_id`
**When** status is requested
**Then** response includes export FSM state, `export_id`, identity key, and provenance summary fields.

**Given** unknown or unauthorized export ID
**When** status is requested
**Then** no-existence-leak policy is applied (`404`).

### Story 6.5: Issue Strictly Scoped Signed Download URL

As an editor,
I want a secure signed download URL for completed exports,
So that I can retrieve deliverables safely.

**Acceptance Criteria:**

**Given** export state is `SUCCEEDED`
**When** download URL is issued
**Then** URL is signed with strict resource scoping to that artifact only
**And** URL TTL follows policy (for example 15 minutes, or contract or config value)
**And** credential material is never logged.

**Given** export state is not `SUCCEEDED`
**When** download retrieval is attempted
**Then** API returns contract-defined state error
**And** no signed URL is issued.

### Story 6.6: Emit Canonical Export Audit Events

As a compliance stakeholder,
I want export actions auditable end-to-end,
So that export lifecycle is traceable and policy-compliant.

**Acceptance Criteria:**

**Given** export lifecycle events occur
**When** audit events are emitted
**Then** event types are exactly `EXPORT_REQUESTED`, `EXPORT_STARTED`, `EXPORT_SUCCEEDED`, and `EXPORT_FAILED`
**And** each includes `export_id` and export identity key plus required audit metadata.

**Given** request or processing is idempotent replay with no new business transition
**When** audit is evaluated
**Then** duplicate idempotent business events are suppressed.
