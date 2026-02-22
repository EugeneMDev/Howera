---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/golden-path.md
  - docs/dev-setup.md
  - spec/sas.md
date: 2026-02-22
author: founder
---

# Product Brief: Howera

## Executive Summary

Howera is a workflow product that turns uploaded video into editable, exportable instruction content with synchronized transcript context and screenshots. The MVP goal is to reduce time-to-first-draft for creators and operators while preserving quality, traceability, and safe resumability in async processing.

The initial product scope is a contract-first API with strict job lifecycle controls, idempotent callbacks, and artifact discipline so workflows can recover safely and evolve across providers. Per SAS, delivery is phased: v1 cloud-first, v2 hybrid with local model options, and v3 fully on-prem/air-gapped.

---

## Core Vision

### Problem Statement

Teams creating instructional content from video currently stitch together transcription, drafting, screenshot capture, and export using multiple manual tools and brittle handoffs. This leads to inconsistent outputs, long cycle time, and poor reproducibility.

### Problem Impact

- Production cycle time is high due to repeated context switching.
- Manual process overhead is substantial; target reduction is 60-80% in documentation effort.
- Quality is inconsistent because artifacts and edits are not managed as a single lifecycle.
- Async failures and retries can corrupt state without explicit idempotency and transition rules.
- Provider lock-in increases migration risk as model or infrastructure needs change.

### Why Existing Solutions Fall Short

- Generic transcript tools do not enforce domain-specific workflow state rules.
- Existing pipelines often skip strict idempotency handling for callbacks.
- Many systems couple business logic to specific AI providers, blocking controlled upgrades.
- Artifact lineage is weak, making auditability and repeatable export difficult.

### Proposed Solution

Build a contract-first service where a Job advances through explicit FSM states from upload confirmation through transcript/draft generation and export. All asynchronous status updates are idempotent, all model access is adapter-isolated, and all assets are tracked in a structured manifest.

### Key Differentiators

- Strict FSM transition gate (`ensure_transition`) for every status change.
- Callback safety by `event_id` idempotency on workflow updates.
- Provider isolation via STT/LLM adapters for controlled switching.
- Artifact manifest discipline across raw and derived assets.
- Golden path E2E scenario as a continuous confidence gate.

## Target Users

### Primary Users

- Content Operators: people converting recordings into publishable instructions and needing fast draft generation with reliable structure.
- Technical Writers: editors refining instruction markdown, preserving anchors, and exporting to final deliverable formats.
- Automation-Minded Builders: engineers integrating workflow orchestration (n8n/FastAPI) who require deterministic behavior and testability.

### Secondary Users

- Team Leads/Product Owners: need visibility into throughput, failure rates, and completion status.
- QA/Compliance Stakeholders: require auditable state transitions and reproducible artifacts.
- Platform Engineers: maintain provider integrations and infrastructure portability over time.

### User Journey

1. Create project and job.
2. Confirm upload with video URI.
3. Start workflow run.
4. Receive staged callbacks (audio ready -> transcript ready -> draft ready).
5. Retrieve and edit instruction markdown.
6. Add and edit screenshots tied to timeline/anchors (extract, adjust frame offset, replace/delete, annotate).
7. Create and retrieve exports (MD bundle, PDF).
8. Re-run or continue safely from checkpoints when partial failures occur.

## Success Metrics

- Time-to-first-draft median <= 10 minutes in mock/local mode for typical fixture size.
- Performance envelope target: under 10 minutes draft generation for a 60-minute video (environment dependent).
- Draft generation completion rate (CREATED -> DRAFT_READY) >= 95% in controlled test runs.
- Finalization completion rate (DRAFT_READY -> DONE, where DONE means at least one export is completed successfully and retrievable) >= 90% in controlled test runs.
- Duplicate callback safety: 100% of repeated `event_id` updates produce no duplicate state mutation.
- Export reliability: >= 99% successful completion for supported formats in non-chaos conditions.
- Developer confidence: golden path test stable on every PR in mock mode.

### Business Objectives

- Deliver a reliable v1 MVP foundation for iterative feature growth.
- Achieve measurable documentation time reduction aligned with the 60-80% target.
- Minimize operational risk through explicit lifecycle and auditability.
- Reduce migration cost by isolating provider-specific dependencies.
- Enable a repeatable content pipeline for teams producing instructional assets at scale.

### Key Performance Indicators

- API flow conversion by stage:
  - `% jobs confirmed upload`
  - `% jobs started`
  - `% jobs reaching DRAFT_READY`
  - `% jobs reaching DONE`
- Reliability:
  - callback dedupe hit rate and safety pass rate
  - invalid transition rejection count
- Throughput:
  - median and p95 time per pipeline stage
- Quality:
  - instruction edit/save success rate
  - screenshot add/edit success rate
  - export completion SLA attainment

## MVP Scope

### Core Features

- Contract-first FastAPI endpoints as defined in `spec/api/openapi.yaml`.
- Project and Job lifecycle endpoints including upload confirmation and run trigger.
- Internal workflow callback endpoint secured with callback secret and idempotency key.
- FSM-validated state transitions with immutable terminal states and checkpoint preservation.
- Transcript retrieval and instruction read/update.
- Screenshot adding and editing in v1, including extraction by timestamp, frame offset adjustment, replacement/deletion, and annotation operation tracking.
- Export creation and status retrieval for `PDF` and `MD_ZIP`.
- Artifact manifest tracking for video/audio/transcript/draft/exports.
- Access model in v1: all authenticated users have the same `editor` role and can access only their own projects.
- Security baseline support: authenticated writes, per-user project isolation, time-limited signed URLs, and audit events for status changes/exports/regenerate.
- Golden path E2E test in mock mode.

### Out of Scope for MVP

- New endpoints or response shapes outside existing OpenAPI contract.
- Full multi-tenant analytics dashboards.
- Advanced collaborative editing and permissions granularity beyond baseline auth.
- Project sharing/collaboration across users (each user works only with own projects in v1).
- Provider-specific optimization features that break adapter abstraction.
- Large-scale production hardening beyond MVP reliability targets.

### MVP Success Criteria

- Golden path scenario executes end-to-end in mock mode with deterministic outputs.
- Contract checks pass with implementation matching OpenAPI schema behavior.
- FSM transition unit tests cover valid and invalid transitions.
- Duplicate callback events are no-op and do not mutate state twice.
- `DRAFT_READY` is reached when LLM draft generation is complete.
- `DONE` is reached when at least one export (`PDF` or `MD_ZIP`) is completed successfully and retrievable.
- Core export formats are generated and retrievable via API contract.

### Future Vision

- Hybrid/local and on-prem variants with the same domain contract and adapter boundaries.
- Expanded editing intelligence (targeted regeneration UX and richer instruction tooling).
- Better observability and operational dashboards for orchestration health.
- Advanced artifact lineage and versioned derived asset management.
- Team-scale workflow controls (policy rules, approvals, and richer audit surfaces).
