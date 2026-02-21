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
- POST /jobs/{jobId}/run → status = AUDIO_EXTRACTING (or queued equivalent before callback)
- Callback updates → AUDIO_READY → TRANSCRIPT_READY → DRAFT_READY

### Instructions
- GET instruction returns markdown
- PUT instruction increments version
- POST regenerate returns task model
- GET /tasks/{taskId} polls regenerate task until SUCCEEDED/FAILED

### Screenshots
- Extract frame by timestamp
- Anchor linked to instruction block
- Annotation operation log persisted

### Export
- MD bundle contains:
  - markdown file
  - referenced images
- PDF renders markdown content

---

## Non-Functional Acceptance Criteria

- FSM enforcement prevents illegal transitions
- Idempotent workflow callback handling
- No direct storage writes without repo abstraction
- No business logic in route handlers
- Adapter pattern used for STT and LLM
