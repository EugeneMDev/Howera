"""Export lifecycle transition rules."""

from app.errors import ApiError
from app.schemas.job import ExportStatus

_TERMINAL_STATES: set[ExportStatus] = {
    ExportStatus.SUCCEEDED,
    ExportStatus.FAILED,
}

_ALLOWED_TRANSITIONS: dict[ExportStatus, set[ExportStatus]] = {
    ExportStatus.REQUESTED: {ExportStatus.RUNNING},
    ExportStatus.RUNNING: {ExportStatus.SUCCEEDED, ExportStatus.FAILED},
    ExportStatus.SUCCEEDED: set(),
    ExportStatus.FAILED: set(),
}


def allowed_next_statuses(status: ExportStatus) -> list[ExportStatus]:
    """Return deterministically ordered allowed successors for an export status."""
    return sorted(_ALLOWED_TRANSITIONS.get(status, set()), key=lambda s: s.value)


def ensure_export_transition(old_status: ExportStatus, new_status: ExportStatus) -> None:
    """Validate export transition according to lifecycle rules."""
    if old_status in _TERMINAL_STATES:
        raise ApiError(
            status_code=409,
            code="EXPORT_TERMINAL_IMMUTABLE",
            message="Terminal export state cannot be mutated",
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
            code="EXPORT_TRANSITION_INVALID",
            message="Invalid export status transition",
            details={
                "current_status": old_status,
                "attempted_status": new_status,
                "allowed_next_statuses": allowed_next,
            },
        )
