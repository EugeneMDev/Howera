# Job FSM — Howera (Source of Truth)

**File:** `spec/domain/job_fsm.md`  
**Purpose:** Formal finite state machine for Job lifecycle.  
**Applies to:** v1 MVP (Firebase + OpenAI), v2 Hybrid, v3 On-prem (behavior unchanged; only providers/infrastructure differ).

---

## 1. Overview

A **Job** represents a single end-to-end processing run from uploaded video to generated draft, edited instruction, and exported artifacts.

FSM goals:
- Deterministic, testable lifecycle
- Resume/retry with checkpoints
- Idempotent processing callbacks
- Explicit terminal states

---

## 2. State Definitions

### 2.1 Primary states (ordered)
- `CREATED` — Job created, no upload initiated.
- `UPLOADING` — Upload session initiated (optional if direct upload).
- `UPLOADED` — Video is available in storage and verified (post `confirm-upload`).
- `AUDIO_EXTRACTING` — Extracting audio from video.
- `AUDIO_READY` — Audio artifact stored; safe checkpoint.
- `TRANSCRIBING` — Running speech-to-text on audio.
- `TRANSCRIPT_READY` — Transcript stored; safe checkpoint.
- `GENERATING` — Generating instruction draft using LLM.
- `DRAFT_READY` — Draft markdown stored; safe checkpoint.
- `EDITING` — User is editing instruction in UI.
- `REGENERATING` — Regenerating selected fragment (async task model).
- `EXPORTING` — Generating export artifacts (PDF/MD bundle).
- `DONE` — Export complete (at least one export succeeded and is retrievable).

### 2.2 Terminal states
- `FAILED` — Terminal failure (non-recoverable automatically).
- `CANCELLED` — Cancelled by user/admin.
- `DONE` — Terminal completion state.

---

## 3. Events and Actors

### 3.1 Actors
- **API**: job creation, upload confirmation, run trigger, cancel, edit/save, export trigger.
- **Workflow Orchestrator (n8n)**: executes heavy steps, sends callbacks to API.
- **User (Editor)**: triggers edits, regenerate, export.
- **System**: scheduled cleanup, retries (if implemented).

### 3.2 Event IDs and idempotency (MANDATORY)
Every state-changing callback from workflow must include:
- `event_id` (string UUID/ULID)
- `job_id`
- `target_status`
- `occurred_at` timestamp

**Idempotency rule:**
- First accepted callback returns `204`.
- If the same `event_id` is replayed with identical payload for `job_id`, the API MUST return `200` with replay metadata and perform **no additional side effects**.

Recommended header:
- `X-Event-Id: <event_id>`  
Or body field `event_id`.

---

## 4. Transition Table (Source of Truth)

Legend:
- ✅ Allowed
- ❌ Not allowed
- ↩ Retry allowed (re-enter same processing state)
- ⏭ Resume allowed from checkpoint (skip completed steps)

### 4.1 Upload & start
| From          | To            | Trigger | Notes |
|---------------|---------------|---------|------|
| (none)        | CREATED       | API     | Create job |
| CREATED       | UPLOADING     | API     | Optional if using resumable session |
| CREATED       | UPLOADED      | API     | If upload happens out-of-band and is confirmed |
| UPLOADING     | UPLOADED      | API     | `confirm-upload` success |
| CREATED       | CANCELLED     | API     | Cancel before upload |
| UPLOADING     | CANCELLED     | API     | Cancel during upload |
| UPLOADED      | CANCELLED     | API     | Cancel before processing |

### 4.2 Processing pipeline
| From             | To               | Trigger | Notes |
|------------------|------------------|---------|------|
| UPLOADED         | AUDIO_EXTRACTING | API/WF  | `run` starts workflow; orchestrator may immediately set this |
| AUDIO_EXTRACTING | AUDIO_READY      | WF      | Audio stored |
| AUDIO_EXTRACTING | FAILED           | WF/API  | See error taxonomy |
| AUDIO_EXTRACTING | AUDIO_EXTRACTING | WF      | ↩ Retry same step (idempotent) |
| AUDIO_READY      | TRANSCRIBING     | WF      | Next step |
| TRANSCRIBING     | TRANSCRIPT_READY | WF      | Transcript stored |
| TRANSCRIBING     | FAILED           | WF/API  | |
| TRANSCRIBING     | TRANSCRIBING     | WF      | ↩ Retry |
| TRANSCRIPT_READY | GENERATING       | WF      | Next step |
| GENERATING       | DRAFT_READY      | WF      | Draft stored |
| GENERATING       | FAILED           | WF/API  | |
| GENERATING       | GENERATING       | WF      | ↩ Retry |
| DRAFT_READY      | EDITING          | API/UI  | User opens editor OR system marks ready for editing |

### 4.3 Editing, regenerate, export
| From        | To            | Trigger | Notes |
|-------------|---------------|---------|------|
| EDITING     | REGENERATING  | API/UI  | Start regenerate task (async); keep editor usable if desired |
| REGENERATING| EDITING       | API/WF  | Task finished (success or fail) |
| EDITING     | EXPORTING     | API/UI  | Start export |
| EXPORTING   | DONE          | WF/API  | Export artifacts ready |
| EXPORTING   | EDITING       | API     | Export failed but job remains editable (preferred) |
| EDITING     | CANCELLED     | API     | Optional policy: allow cancel only if no exports running |

### 4.4 Global transitions (always allowed)
| From (any non-terminal) | To        | Trigger | Notes |
|-------------------------|-----------|---------|------|
| *                       | CANCELLED | API     | Must stop active workflow and mark cancelled |
| *                       | FAILED    | API/WF  | Only for non-recoverable errors or policy violations |

### 4.5 Forbidden transitions (examples, non-exhaustive)
- `CREATED → TRANSCRIBING` (audio not ready)
- `UPLOADING → AUDIO_EXTRACTING` (video not confirmed)
- `FAILED → *` (terminal) unless you implement explicit `RETRY_FROM_FAILED` action (not in v1)
- `CANCELLED → *` (terminal)
- `DONE → *` (terminal)

---

## 5. Checkpoints and Resume Rules

### 5.1 Checkpoint states
- `AUDIO_READY`
- `TRANSCRIPT_READY`
- `DRAFT_READY`

### 5.2 Resume policy
When re-running a job (manual retry or system retry), workflow SHOULD:
- If `audio_uri` exists and verified → resume from `AUDIO_READY`
- If transcript exists and verified → resume from `TRANSCRIPT_READY`
- If draft exists and verified → resume from `DRAFT_READY` (usually skip generation, go to editing)

### 5.3 Re-run entry points (recommended API behavior)
- `POST /jobs/{jobId}/run` is allowed only when:
  - status in `{UPLOADED, AUDIO_READY, TRANSCRIPT_READY, DRAFT_READY}`  
  - and job not terminal.
- Re-run MUST NOT delete existing artifacts; it may create new versions.

---

## 6. Error Taxonomy and Failure Policy

### 6.1 Error classes
**RETRYABLE (automatic retry allowed)**
- transient network errors to STT/LLM provider
- timeouts
- temporary storage read/write failures
- rate limiting (with backoff)

**NON_RETRYABLE (fail fast)**
- unsupported video codec/format (after normalization attempt)
- invalid auth/permission for provider
- corrupted input artifacts (video/audio) after verification
- schema validation failure that indicates bad pipeline configuration
- policy violations (e.g., disallowed model)

### 6.2 Failure mapping
- If error is RETRYABLE and retry budget not exhausted:
  - stay in same processing state (↩) and emit retry event
- If retry budget exhausted OR NON_RETRYABLE:
  - transition to `FAILED` with `failure_reason` populated

### 6.3 Required fields on failure (minimum)
- `failure_code` (string)
- `failure_message` (string, human readable)
- `failed_stage` (one of processing stages)
- `correlation_id` (traceable to logs/workflow run)

---

## 7. Concurrency & Locking Rules

### 7.1 Single active pipeline rule
- A job MUST NOT have more than one active processing pipeline instance at a time.
- API MUST enforce a lock for transitions into:
  - `AUDIO_EXTRACTING`, `TRANSCRIBING`, `GENERATING`, `EXPORTING`

### 7.2 Regenerate tasks
- Multiple regenerate tasks MAY be allowed, but recommended v1 rule:
  - Allow only 1 active regenerate per instruction to avoid merge conflicts.
- If another regenerate is requested while `REGENERATING`:
  - return `409 Conflict` with active task id (recommended)

---

## 8. Required Status Update Payload (Workflow → API)

**Endpoint:** `POST /internal/jobs/{jobId}/status` (or equivalent)  
**Required fields:**
- `event_id`
- `status` (target status)
- `occurred_at`
- `artifact_updates` (optional map)
- `failure_*` fields (if transitioning to FAILED)

**Artifact updates keys (examples):**
- `audio_uri`
- `transcript_uri`
- `draft_uri`
- `export_uri`
- `metrics` (duration, token usage, etc.)

---

## 9. Acceptance Tests (FSM)

Minimum test suite MUST include:
1. **Allowed transitions**: all rows in transition table that are ✅
2. **Forbidden transitions**: representative invalid moves (at least 1 per stage)
3. **Terminal behavior**: no transition out of `FAILED`, `CANCELLED`, and `DONE`
4. **Idempotency**: same `event_id` applied twice does not duplicate effects
5. **Resume**: from `AUDIO_READY` skips extraction; from `TRANSCRIPT_READY` skips STT

---

## 10. Future Extensions (Not in v1)

Optional states/actions if needed later:
- `ARCHIVED` (immutable final)
- explicit `RETRY_FROM_FAILED` action (non-terminal fail)
- `VALIDATING` (pre-flight checks before running)
- `NORMALIZING_VIDEO` (transcode step)
