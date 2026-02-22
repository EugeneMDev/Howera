# Acceptance Criteria — v1 MVP (Firebase + OpenAI + FastAPI)

## Definition of Done (System Level)

The system is considered MVP-ready when:

1. A user can:
   - Authenticate via Firebase JWT
   - Create a project
   - Create a job
   - Upload a video
   - Confirm upload
   - Trigger workflow
   - Receive draft instruction
   - Edit instruction
   - Extract at least one screenshot
   - Export MD bundle
   - Export PDF

2. Job lifecycle strictly follows FSM rules defined in:
   spec/domain/job_fsm.md

3. OpenAPI contract:
   - All endpoints from spec/api/openapi.yaml exist
   - No undocumented endpoints
   - Schema responses validated via pydantic

4. All business logic passes:
   - Unit tests
   - FSM transition tests
   - At least 1 Golden Path e2e test (mock providers)

5. make check == green

---

## Functional Acceptance Criteria

### Projects
- POST /projects creates project
- GET /projects returns list
- GET /projects/{projectId} returns project

### Jobs
- POST /projects/{projectId}/jobs → status = CREATED
- POST /jobs/{jobId}/confirm-upload → status = UPLOADED
- POST /jobs/{jobId}/run → `202` on first dispatch, `200` on idempotent replay
- POST /jobs/{jobId}/cancel enforces FSM-cancellable states only
- POST /jobs/{jobId}/retry allowed only from FAILED with checkpoint-aware metadata
- Callback updates → AUDIO_READY → TRANSCRIPT_READY → DRAFT_READY
- Callback first apply returns `204`, idempotent replay returns `200` no-op

### Instructions
- GET instruction returns latest (or requested) versioned markdown payload
- PUT instruction enforces optimistic concurrency (`base_version`) and increments version
- POST regenerate returns task model (`202`, `200` replay)
- GET /tasks/{taskId} polls regenerate task until SUCCEEDED/FAILED

### Screenshots & Anchors
- POST /jobs/{jobId}/screenshots/extract is async (`202`) with screenshot task polling via GET /screenshot-tasks/{taskId}
- POST /instructions/{instructionId}/anchors, GET /instructions/{instructionId}/anchors, and GET /anchors/{anchorId} manage anchor lifecycle
- POST /anchors/{anchorId}/replace supports idempotent replacement with asset version linkage
- DELETE /anchors/{anchorId}/assets/{assetId} performs soft-delete with deterministic active fallback
- POST /jobs/{jobId}/screenshots/uploads and POST /jobs/{jobId}/screenshots/uploads/{uploadId}/confirm support custom image upload
- POST /anchors/{anchorId}/attach-upload attaches confirmed upload to anchor
- POST /anchors/{anchorId}/annotations persists annotation operation log and deterministic rendered asset

### Export
- POST /jobs/{jobId}/exports is idempotent by deterministic export identity key
- GET /exports/{exportId} returns status in REQUESTED/RUNNING/SUCCEEDED/FAILED
- download_url is present only when export status is SUCCEEDED
- Job reaches DONE only after at least one export succeeds and is retrievable

---

## Non-Functional Acceptance Criteria

- FSM enforcement prevents illegal transitions
- Idempotent workflow callback handling
- No-existence-leak policy: unauthorized and nonexistent resources return the same 404 shape
- No direct storage writes without repo abstraction
- No business logic in route handlers
- Adapter pattern used for STT and LLM
