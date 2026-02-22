"""Job API schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class JobStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    AUDIO_EXTRACTING = "AUDIO_EXTRACTING"
    AUDIO_READY = "AUDIO_READY"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSCRIPT_READY = "TRANSCRIPT_READY"
    GENERATING = "GENERATING"
    DRAFT_READY = "DRAFT_READY"
    EDITING = "EDITING"
    REGENERATING = "REGENERATING"
    EXPORTING = "EXPORTING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ArtifactManifest(BaseModel):
    video_uri: str | None = None
    audio_uri: str | None = None
    transcript_uri: str | None = None
    draft_uri: str | None = None
    exports: list[str] | None = None


class Job(BaseModel):
    id: str
    project_id: str
    status: JobStatus
    manifest: ArtifactManifest | None = None
    created_at: datetime
    updated_at: datetime | None = None
