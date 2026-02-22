# AGENTS.md
Project: Howera
Architecture: FastAPI + Firebase (v1) + n8n + OpenAI
Agent Model: GPT-5.3-Codex

This document defines mandatory operational rules for all coding agents
working in this repository.

---

## 1. Source of Truth

- The `spec/` directory is the authoritative source of truth.
- Do NOT modify anything under `spec/` unless the task explicitly allows it.
- Code must adapt to spec — never the other way around.

---

## 2. Contract-First API

- All endpoints must strictly follow `spec/api/openapi.yaml`.
- Do NOT introduce new endpoints, fields, or status codes
  unless the OpenAPI spec is updated in a separate task.
- Request and response bodies must use Pydantic models.

Before completing a task:
- Verify `/openapi.json` includes the expected paths.
- Ensure response schemas match the contract.

---

## 3. FSM Enforcement (Job Lifecycle)

- All Job status transitions must go through:
  `domain/job_fsm.ensure_transition(old_status, new_status)`
- Direct assignment like `job.status = X` is forbidden.
- Terminal states (FAILED, CANCELLED, DONE) are immutable.
- Checkpoint states (AUDIO_READY, TRANSCRIPT_READY, DRAFT_READY)
  must be preserved to support resumability.

Unit tests for valid/invalid transitions are mandatory.

---

## 4. Workflow Safety & Idempotency

- All async workflow callbacks must include an idempotency key (`event_id`).
- Duplicate callbacks must be no-op.
- State transitions must be validated through FSM before update.
- Artifact writes must be atomic or logically consistent.

Never implement side effects without idempotency protection.

---

## 5. Provider Isolation

- All STT and LLM calls must go through adapters:
  - `adapters/stt/*.py`
  - `adapters/llm/*.py`
- Business logic must never call OpenAI SDK directly.
- Adapter output must be normalized to internal models.

This guarantees provider switching (v1 → v2 → v3).

---

## 6. Artifact Discipline

- Every Job must maintain an `artifact_manifest`.
- Raw artifacts (video, audio, transcript) are immutable.
- Derived assets (screenshots, exports) must be versioned and linked.
- No anonymous files in storage.

---

## 7. Minimal Diff Discipline

- Modify only files required by the task.
- Do not refactor unrelated modules.
- Avoid formatting-only commits.
- One task = one logical change set.

---

## 8. Proof Before Done

A task is NOT complete until:

- `make lint` passes
- `make test` passes
- `make check` passes
- A summary is provided:
  - What changed
  - Why
  - How verified

Never mark work as complete without verification.

---

## 9. Security Baseline

- All write endpoints require authentication.
- Signed URLs must be time-limited.
- Never log secrets or raw transcripts.
- Audit events must be generated for:
  - status transitions
  - exports
  - regenerate actions

---

Failure to follow these rules invalidates the task.
