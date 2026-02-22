---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-11-complete
  - step-12-complete
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-Howera-2026-02-22.md
  - docs/golden-path.md
  - docs/dev-setup.md
  - spec/sas.md
  - spec/api/openapi.yaml
workflowType: 'prd'
documentCounts:
  briefCount: 1
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 2
classification:
  projectType: api_backend
  domain: general
  complexity: low
  projectContext: brownfield
---

# Product Requirements Document - Howera

**Author:** founder
**Date:** 2026-02-22

## Executive Summary

Howera is a workflow-driven platform that converts uploaded instructional/demo videos into structured Markdown instructions with transcript grounding, screenshot support, and final export artifacts. The v1 product is an API-first implementation with strict state control and resumable async processing.

The product addresses high manual effort and inconsistent quality in documentation workflows. Based on SAS goals, Howera targets a 60-80% reduction in documentation effort while preserving deterministic output quality and auditability.

v1 is cloud-first (Firebase + OpenAI), with deliberate architecture boundaries that enable v2 hybrid (local model options) and v3 on-prem evolution without rewriting core business logic.

### What Makes This Special

- Contract-first implementation with `spec/api/openapi.yaml` as binding API source.
- Enforced job lifecycle FSM with checkpoint preservation and terminal state immutability.
- Callback idempotency and replay safety using `event_id`.
- Provider abstraction boundaries for STT and LLM integrations.
- Artifact manifest discipline and export traceability.

## Project Classification

- Project Type: `api_backend`
- Domain: `general` (workflow/documentation automation with security-sensitive deployment options)
- Complexity: `low` by domain taxonomy, with high operational rigor requirements
- Context: `brownfield` (existing specs/docs and architecture constraints already defined)

## Success Criteria

### User Success

- Editors can complete the golden path from project creation to export without manual backend intervention.
- Users can retrieve and update instruction content reliably after draft generation.
- Users can request screenshot extraction at specific timestamps and receive anchor metadata for insertion workflows.
- Users experience predictable workflow behavior under retries or duplicate callbacks.

### Business Success

- Demonstrate measurable cycle-time reduction aligned with SAS target (60-80%) on pilot teams.
- Maintain release confidence via deterministic mock-mode E2E tests on each PR.
- Keep provider migration risk low by preventing direct provider coupling in business logic.
- Establish a stable v1 platform that can evolve to hybrid/on-prem deployments with minimal domain-layer changes.

### Technical Success

- 100% state transitions pass through FSM transition validation.
- Duplicate callback replay with identical `event_id` is no-op and does not duplicate mutations.
- OpenAPI contract and implementation remain aligned for paths, schemas, and status behavior.
- Core artifacts (video/audio/transcript/draft/exports) remain discoverable through manifest linkage.

### Measurable Outcomes

- `DRAFT_READY` attainment rate >= 95% for valid jobs in controlled test runs.
- `DONE` attainment rate >= 90% when export workflows are triggered.
- Duplicate callback safety pass rate = 100% in callback idempotency tests.
- Export completion success >= 99% for `PDF` and `MD_ZIP` under non-chaos conditions.
- Performance envelope target: draft generation under 10 minutes for a 60-minute input video (environment dependent).

## Product Scope

### MVP - Minimum Viable Product

- Contract-compliant project/job/instruction/screenshot/export/internal-callback API.
- Job lifecycle from `CREATED` through async processing checkpoints to export completion.
- Workflow orchestration integration via n8n callback model.
- Transcript retrieval, instruction update, regenerate request initiation, and task status polling.
- Screenshot extraction request handling via timestamp-based API.
- Export request creation and export status retrieval.
- Baseline authentication and callback secret validation.

### Growth Features (Post-MVP)

- AI-assisted screenshot tooling (for example smart frame suggestions, annotation templates, and policy-driven redaction helpers).
- Enhanced audit and observability dashboards.
- Stronger quality tooling for markdown structure validation and style enforcement.
- Expanded integration options for enterprise orchestration and storage backends.

### Vision (Future)

- v2 hybrid deployment with local LLM/STT options configured at environment/pipeline level.
- v3 on-prem architecture with Keycloak, PostgreSQL, MinIO, and self-hosted AI stack.
- Air-gapped deployment readiness for sensitive environments.
- Policy-driven governance and broader enterprise controls.

## User Journeys

### Journey 1: Create First Draft from Video

1. Editor creates a project.
2. Editor creates a job under the project.
3. Editor confirms uploaded video URI.
4. Editor starts workflow run.
5. System progresses through audio/transcript/draft states via callback updates.
6. Editor opens generated instruction content and transcript context.

Outcome: User reaches editable draft quickly with system-managed async pipeline.

### Journey 2: Refine Instruction Content

1. Editor fetches instruction by ID.
2. Editor updates markdown content and saves.
3. Editor optionally requests partial regeneration for a selected text fragment.
4. Editor polls task status until regeneration completes.

Outcome: User iterates content without re-running full workflow.

### Journey 3: Add Visual Context

1. Editor requests screenshot extraction at target timestamp.
2. Editor polls screenshot task until completion and retrieves resulting anchor/asset metadata.
3. Editor optionally replaces, uploads, deletes, or annotates screenshot assets linked to anchors.
4. Editor uses the active anchor asset in document workflow.

Outcome: Instruction quality improves with time-aligned visual support.

### Journey 4: Publish Export

1. Editor requests `MD_ZIP` or `PDF` export.
2. System marks export as async process.
3. Editor checks export status and retrieves download URL when export is `SUCCEEDED`.
4. Job status becomes `DONE` after first successful export.

Outcome: User receives deliverable artifact for sharing/publication.

### Journey Requirements Summary

- Each journey must be recoverable after transient failures.
- Each state-changing action must be authenticated and auditable.
- Asynchronous updates must preserve consistency and prevent duplicate side effects.

## Domain-Specific Requirements

This project is classified under `general`, but it must satisfy stricter operational rules due to asynchronous automation and sensitive content handling.

### Compliance & Governance

- Enforce authenticated write endpoints.
- Use time-limited signed URLs for storage access operations.
- Record audit events for status transitions, exports, and regenerate actions.

### Data & Privacy

- Never log secrets or raw transcript payloads in application logs.
- Keep raw artifacts immutable and version derived outputs.
- Maintain clear artifact traceability for all generated/exported outputs.

### Operational Safety

- Ensure idempotent processing for callback and retry scenarios.
- Preserve checkpoint states to support resumability and support operations.

## Innovation & Novel Patterns

### Detected Innovation Areas

- Single workflow domain model that remains stable across cloud-first, hybrid, and on-prem phases.
- Strict contract+FSM+idempotency combination used as a reliability backbone for AI workflows.

### Market Context & Competitive Landscape

- Typical video-to-doc tools optimize convenience but often under-specify lifecycle consistency and resumability.
- Howera differentiates through operational rigor suitable for enterprise and sensitive deployments.

### Validation Approach

- Golden path E2E in mock mode on every PR.
- Focused transition/idempotency test suites for high-risk workflow boundaries.
- Contract checks against generated `/openapi.json`.

### Risk Mitigation

- Prevent provider lock-in using STT/LLM adapters.
- Keep business logic independent from provider SDK calls.
- Use phased delivery to control migration and operational risk.

## API Backend Specific Requirements

### API Contract Management

- Implementation MUST conform to `spec/api/openapi.yaml`.
- No unapproved endpoints, fields, or status codes in v1.
- Request/response payloads use Pydantic models and schema-compatible field names.

### Security & Access Model

- All write endpoints require bearer authentication.
- Internal callback endpoint requires callback secret validation.
- Authorization decisions must prevent cross-project data access between users.

### Async Workflow Integration

- `POST /jobs/{jobId}/run` triggers orchestrator workflow.
- `POST /internal/jobs/{jobId}/status` applies validated callback events.
- Duplicate `event_id` callbacks are processed as no-op.

### API Reliability Considerations

- API must remain deterministic under callback reorder/duplication scenarios.
- Errors should be explicit and contract-consistent.
- Long-running processing handled asynchronously with polling/status APIs.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

Deliver a narrow but reliable end-to-end slice that proves value and sets architecture constraints for later phases. Prioritize state integrity and contract stability over feature breadth.

### MVP Feature Set (Phase 1)

- Project and job management basics.
- Upload confirmation and workflow start.
- Callback-driven status transitions with FSM enforcement.
- Transcript retrieval and instruction CRUD basics.
- Regenerate task creation/status retrieval.
- Screenshot and anchor lifecycle APIs (extract, replace, delete, upload/attach, annotate).
- Export creation and status retrieval (`PDF`, `MD_ZIP`).
- Security baseline and audit trail requirements.

### Post-MVP Features

- Advanced screenshot collaboration workflows and richer editor UX.
- Richer collaboration and permissions.
- Deployment profile automation for hybrid/on-prem bundles.
- Enhanced operational analytics and SLO dashboards.

### Risk Mitigation Strategy

- Keep API changes contract-driven and explicitly versioned.
- Add tests for each transition rule before expanding workflow branches.
- Gate high-risk changes with golden-path and callback-idempotency test coverage.

## Functional Requirements

### Identity & Access

- FR-001: Authenticated user can create a project.
- FR-002: Authenticated user can list and retrieve only their own projects.
- FR-003: Authenticated user can create a job under a project they own.
- FR-004: Authenticated user can retrieve status for a job they own.
- FR-005: System validates callback secret for internal workflow callback endpoint.

### Job Lifecycle Management

- FR-006: User can confirm upload for a job by submitting `video_uri`.
- FR-007: System can transition job state only via allowed FSM transitions.
- FR-008: System must prevent mutation of terminal states (`FAILED`, `CANCELLED`, `DONE`).
- FR-009: User can trigger workflow execution for an uploaded job.
- FR-010: System stores and updates artifact manifest as lifecycle progresses.
- FR-011: System preserves checkpoint states (`AUDIO_READY`, `TRANSCRIPT_READY`, `DRAFT_READY`) for resumability.

### Callback & Idempotency

- FR-012: Internal callback can submit `event_id`, `status`, and `occurred_at`.
- FR-013: System detects duplicate `event_id` and treats duplicate callback as no-op.
- FR-014: Callback status updates must be rejected when violating FSM transition rules.
- FR-015: Callback processing can attach artifact updates consistently with state changes.
- FR-016: Callback processing can record failure metadata (`failure_code`, `failure_message`, `failed_stage`).

### Transcript & Instruction Authoring

- FR-017: User can retrieve transcript segments for a job.
- FR-018: User can retrieve instruction content by instruction ID.
- FR-019: User can update instruction markdown and receive updated instruction version metadata.
- FR-020: User can request targeted regeneration on instruction selection range.
- FR-021: User can query regenerate task status until completion/failure.

### Screenshot & Media Operations

- FR-022: User can request screenshot extraction for a job at `timestamp_ms`.
- FR-023: Screenshot extraction accepts optional alignment parameters (`offset_ms`, strategy, format) per API contract.
- FR-024: System returns screenshot anchor details including `asset_id`, `image_uri`, and dimensions.

### Export Management

- FR-025: User can request export generation for supported formats (`PDF`, `MD_ZIP`).
- FR-026: System provides export status retrieval by export ID.
- FR-027: System returns downloadable URL for completed exports.
- FR-028: System associates export artifacts with originating job manifest/history.

### Auditability & Governance

- FR-029: System records auditable events for status transitions.
- FR-030: System records auditable events for export requests/completions.
- FR-031: System records auditable events for regenerate requests.
- FR-032: System avoids storing secrets or raw transcript text in logs.

### Screenshot & Anchor Lifecycle

- FR-033: User can replace an existing screenshot asset linked to an anchor by requesting a new extraction with updated `timestamp_ms` and/or `offset_ms`.
- FR-034: User can delete (soft-delete) a screenshot asset and unlink it from its anchor without mutating immutable raw artifacts.
- FR-035: User can upload a custom image file and attach it to an existing or new screenshot anchor.
- FR-036: User can create and update screenshot annotations (for example blur, arrow, marker, pencil) stored as an operation log and associated rendered image artifact.
- FR-037: System supports creation and retrieval of screenshot anchors linked to instruction version blocks (`block_id`) or approved fallback strategy.
- FR-038: System ensures anchor stability across instruction version updates according to defined anchor persistence policy.

### Export Determinism & Version Control

- FR-039: Export request must reference a specific instruction version identifier.
- FR-040: System guarantees export reproducibility by associating each export artifact with instruction version ID, linked screenshot asset versions, and generation timestamp.

### Job Control & Recovery

- FR-041: User can cancel a running job when allowed by FSM transition rules.
- FR-042: User can retry a failed job from the latest valid checkpoint state without duplicating prior completed stages.

### Model & Prompt Configuration

- FR-043: System supports selection of model profile (for example cloud or local provider) per environment or job configuration according to allowed policies.
- FR-044: System stores and links system prompt template and prompt parameters used during draft generation to ensure reproducibility and auditability.

### Instruction Quality & Validation

- FR-045: System validates generated instruction markdown against a minimal structural schema (for example step structure and headings) and records validation status.

## Non-Functional Requirements

### Performance

- NFR-001: System should target draft generation completion under 10 minutes for a 60-minute video in baseline target environment.
- NFR-002: Job status retrieval endpoints should return within interactive API latency expectations for normal load.
- NFR-003: Callback handling should complete quickly enough to avoid orchestrator timeout/retry cascades.

### Security

- NFR-004: All write operations require authenticated identity validation.
- NFR-005: Internal callback endpoint requires shared-secret verification.
- NFR-006: Signed URLs for storage access must be time-limited.
- NFR-007: Secrets must be sourced from environment/secret management and never logged.

### Scalability

- NFR-008: Asynchronous workflow architecture must support horizontal worker/orchestrator scaling.
- NFR-009: Design must permit provider replacement and deployment-mode evolution without business-domain rewrites.

### Accessibility

- NFR-010: Any user-facing web surfaces in scope should target WCAG-aligned accessibility baseline as practical for MVP.

### Integration

- NFR-011: API and orchestrator integration must use stable contract payloads for run/callback flows.
- NFR-012: STT/LLM integrations must pass through adapters with normalized internal outputs.
- NFR-013: CI quality gates must include lint/test/check and golden-path validation in mock mode.

## Assumptions & Open Questions

- The current OpenAPI contract already exposes screenshot and anchor lifecycle endpoints required for v1 scope.
- Access-control detail beyond authenticated editor baseline may require explicit RBAC decisions in future phases.
- Storage retention windows from SAS should be translated into enforceable policy/config items in implementation planning.

### Contract Semantics To Align Before Implementation

- Idempotency and replay semantics must be explicit in OpenAPI for confirm-upload, run, callback, regenerate, screenshot, and export flows.
- Error semantics should be codified with contract-level codes for transition, version, replay, ordering, and dispatch failures.
- No-existence-leak behavior should be defined consistently for unauthorized/not-found resource access.
- Export determinism must be represented in contract schemas (identity key, provenance references, immutable success snapshot).
