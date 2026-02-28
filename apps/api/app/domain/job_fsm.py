"""Job lifecycle transition rules."""

from app.errors import ApiError
from app.schemas.job import JobStatus

_TERMINAL_STATES: set[JobStatus] = {
    JobStatus.FAILED,
    JobStatus.CANCELLED,
    JobStatus.DONE,
}

_ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.CREATED: {JobStatus.UPLOADING, JobStatus.UPLOADED, JobStatus.CANCELLED},
    JobStatus.UPLOADING: {JobStatus.UPLOADED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.UPLOADED: {JobStatus.AUDIO_EXTRACTING, JobStatus.CANCELLED},
    JobStatus.AUDIO_EXTRACTING: {JobStatus.AUDIO_EXTRACTING, JobStatus.AUDIO_READY, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.AUDIO_READY: {JobStatus.TRANSCRIBING, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.TRANSCRIBING: {JobStatus.TRANSCRIBING, JobStatus.TRANSCRIPT_READY, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.TRANSCRIPT_READY: {JobStatus.GENERATING, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.GENERATING: {JobStatus.GENERATING, JobStatus.DRAFT_READY, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.DRAFT_READY: {JobStatus.EDITING, JobStatus.REGENERATING, JobStatus.EXPORTING, JobStatus.DONE},
    JobStatus.EDITING: {JobStatus.REGENERATING, JobStatus.EXPORTING, JobStatus.DONE, JobStatus.CANCELLED},
    JobStatus.REGENERATING: {JobStatus.DRAFT_READY, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.EXPORTING: {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.DONE: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}


def allowed_next_statuses(status: JobStatus) -> list[JobStatus]:
    """Return deterministically ordered allowed successors for a status."""
    return sorted(_ALLOWED_TRANSITIONS.get(status, set()), key=lambda s: s.value)


def ensure_transition(old_status: JobStatus, new_status: JobStatus) -> None:
    """Validate transition according to lifecycle rules."""
    if old_status in _TERMINAL_STATES:
        raise ApiError(
            status_code=409,
            code="FSM_TERMINAL_IMMUTABLE",
            message="Terminal state cannot be mutated",
            details={
                "current_status": old_status,
                "attempted_status": new_status,
                "allowed_next_statuses": [],
            },
        )

    allowed_next = allowed_next_statuses(old_status)
    if new_status not in _ALLOWED_TRANSITIONS.get(old_status, set()):
        raise ApiError(
            status_code=409,
            code="FSM_TRANSITION_INVALID",
            message="Invalid status transition",
            details={
                "current_status": old_status,
                "attempted_status": new_status,
                "allowed_next_statuses": allowed_next,
            },
        )
