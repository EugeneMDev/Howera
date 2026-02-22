# Project Context – Howera

Last Updated: 2026-02-22  
Architecture Phase: v1 MVP (Firebase + OpenAI)  
Backend: FastAPI  
Workflow: n8n  
Agent Model: GPT-5.3-Codex  

---

# 1. Project Purpose

Howera is a workflow-driven system that converts uploaded instructional/demo videos into structured, editable Markdown instructions with transcript grounding, screenshot support, and export artifacts.

The core goal of v1 is:

> Deliver a deterministic, resumable, contract-first async pipeline from video upload to export.

The system is designed to:

- Reduce documentation effort by 60–80%.
- Maintain strict lifecycle integrity.
- Ensure provider independence.
- Support safe retries and resumability.
- Evolve into hybrid and on-prem deployments without domain rewrite.

---

# 2. Architectural Invariants (Non-Negotiable)

These rules must never be violated:

## 2.1 Spec Is Law
- `spec/` directory is authoritative.
- OpenAPI defines the API contract.
- Code must adapt to spec, not vice versa.

## 2.2 FSM Enforcement
- Every Job state change must pass through `ensure_transition`.
- Terminal states are immutable.
- Checkpoint states enable resumability.

## 2.3 Idempotent Async Processing
- All callbacks include `event_id`.
- Duplicate callbacks are no-op.
- Artifact updates must be safe under retry.

## 2.4 Provider Isolation
- STT and LLM integrations must go through adapters.
- No direct OpenAI SDK usage in business logic.
- Business layer must remain provider-agnostic.

## 2.5 Artifact Discipline
- Every Job maintains an artifact manifest.
- Raw artifacts are immutable.
- Derived artifacts are versioned and linked.

---

# 3. System Boundaries

## In Scope (v1)

- Project & Job lifecycle management
- Upload confirmation
- Workflow start trigger
- Async callback processing
- Transcript retrieval
- Instruction CRUD
- Partial regeneration request
- Screenshot and anchor lifecycle (extract, replace, delete, upload, attach, annotate)
- Export creation & retrieval
- Authentication baseline
- Callback secret validation
- Audit logging baseline

## Out of Scope (v1)

- Full multi-user collaboration
- Advanced permissions
- Observability dashboards
- Advanced analytics
- Production hardening for high-scale multi-tenant SaaS

---

# 4. Core Domain Model

## 4.1 Job Lifecycle

Primary states:

CREATED  
UPLOADING  
UPLOADED  
AUDIO_EXTRACTING  
AUDIO_READY  
TRANSCRIBING  
TRANSCRIPT_READY  
GENERATING  
DRAFT_READY  
EDITING  
REGENERATING  
EXPORTING  
DONE  
FAILED  
CANCELLED  

Rules:

- No direct state assignment.
- Invalid transitions must be rejected.
- Duplicate callbacks must not duplicate effects.

---

## 4.2 Artifact Manifest

Each Job must track:

- video_uri
- audio_uri
- transcript_uri
- draft_uri
- screenshot_assets[]
- exports[]

Artifacts must be discoverable and reproducible.

---

## 4.3 Async Model

Synchronous:
- Create project
- Create job
- Confirm upload
- Fetch transcript
- Fetch/update instruction

Asynchronous:
- Workflow processing
- Regenerate
- Export

All async flows must:
- Support polling
- Be idempotent
- Be resumable

---

# 5. Security Model (v1 Baseline)

- All write endpoints require authentication.
- Internal callback endpoint requires shared secret.
- Users can access only their own projects.
- Signed URLs must be time-limited.
- No logging of raw transcripts or secrets.

---

# 6. Deployment Phases

## v1 – Cloud First
- Firebase (Auth/Storage)
- OpenAI (STT + LLM)
- n8n orchestrator
- FastAPI backend

## v2 – Hybrid
- Local LLM/STT option
- Provider switching via adapters
- Same domain model

## v3 – On-Prem
- Keycloak
- PostgreSQL
- MinIO
- Local AI stack
- Air-gapped ready

Domain model must remain unchanged across phases.

---

# 7. Golden Path Scenario (Confidence Gate)

1. Create project
2. Create job
3. Confirm upload
4. Run workflow
5. Reach DRAFT_READY
6. Fetch instruction
7. Request export
8. Reach DONE

Golden path must pass in mock mode on every PR.

---

# 8. Known Constraints

- Performance target: draft under 10 minutes for 60-minute video (environment dependent).
- MVP prioritizes reliability over breadth.
- Concurrency edge cases must be controlled.
- Callback reordering must not corrupt state.

---

# 9. Design Philosophy

- Reliability > Feature Count
- Determinism > Convenience
- Explicit State > Implicit Logic
- Small Increments > Big Refactors
- Clear Contracts > Magic

---

# 10. What This Project Is NOT

- Not just a transcript tool.
- Not a simple CRUD API.
- Not tightly coupled to OpenAI.
- Not allowed to mutate state implicitly.
- Not allowed to ignore failure metadata.

---

# 11. Agent Expectations

When implementing changes:

- Follow AGENTS.md.
- Respect spec contracts.
- Enforce FSM.
- Ensure idempotency.
- Run tests before completion.
- Provide summary of changes.

---

# 12. Future Evolution

The architecture must allow:

- Provider replacement
- Storage backend replacement
- Deployment model changes
- Advanced collaborative annotation workflows
- Enterprise governance features

Without rewriting domain logic.
