# Tests Workflow

## Artifacts

- Planning CSV: `tests/high_risk_cases.csv`
- Stub modules:
  - `tests/api/test_callbacks.py`
  - `tests/api/test_jobs_fsm.py`
  - `tests/api/test_instructions_versioning.py`
  - `tests/api/test_exports_provenance.py`
  - `tests/api/test_anchors_assets.py`

## Contract Between CSV and Pytest

- `test_id` is the stable key and must not be changed once published.
- Every `test_id` in `tests/high_risk_cases.csv` must have exactly one pytest function stub.
- Each stub uses:
  - `@pytest.mark.p0` or `@pytest.mark.p1`
  - `@pytest.mark.test_id("...")`
  - `raise NotImplementedError("test_id=...")` until implemented.

## Updating CSV Fields During Implementation

- `pytest_nodeid`:
  - Keep `TBD` while stub-only.
  - Update to real node id when implemented, e.g.
    - `tests/api/test_jobs_fsm.py::test_run_001`
- `status`:
  - `PLANNED` -> `IN_PROGRESS` -> `IMPLEMENTED` -> `PASSING`
  - Optional failure states: `FAILING`, `BLOCKED`.

## Suggested Implementation Loop

1. Pick a `PLANNED` row from CSV.
2. Implement the matching stub test body.
3. Set `pytest_nodeid` and move `status` to `IMPLEMENTED`.
4. Run tests and move `status` to `PASSING` once green.
5. Keep `test_id` marker unchanged for traceability.
