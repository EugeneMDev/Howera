"""Job API schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.instruction import CharRange


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


class TranscriptSegment(BaseModel):
    start_ms: int
    end_ms: int
    text: str


class TranscriptPage(BaseModel):
    items: list[TranscriptSegment]
    limit: int
    next_cursor: str | None = None


class ConfirmUploadRequest(BaseModel):
    video_uri: str


class ConfirmUploadResponse(BaseModel):
    job: Job
    replayed: bool


class RunJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    dispatch_id: str
    replayed: bool


class RetryJobRequest(BaseModel):
    model_profile: str
    client_request_id: str


class RetryJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    resume_from_status: JobStatus
    checkpoint_ref: str
    model_profile: str
    dispatch_id: str
    replayed: bool


class ScreenshotOperation(str, Enum):
    EXTRACT = "extract"
    REPLACE = "replace"


class ScreenshotTaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ScreenshotTask(BaseModel):
    task_id: str
    operation: ScreenshotOperation
    status: ScreenshotTaskStatus
    anchor_id: str | None = None
    asset_id: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None


class ScreenshotStrategy(str, Enum):
    NEAREST_KEYFRAME = "nearest_keyframe"
    PRECISE = "precise"


class ScreenshotFormat(str, Enum):
    PNG = "png"
    JPG = "jpg"
    WEBP = "webp"


class ScreenshotMimeType(str, Enum):
    PNG = "image/png"
    JPEG = "image/jpeg"
    WEBP = "image/webp"


class ScreenshotAssetKind(str, Enum):
    EXTRACTED = "EXTRACTED"
    UPLOADED = "UPLOADED"
    ANNOTATED = "ANNOTATED"


class AnchorAddressType(str, Enum):
    BLOCK_ID = "block_id"
    CHAR_RANGE = "char_range"


class AnchorResolutionState(str, Enum):
    RETAIN = "retain"
    REMAP = "remap"
    UNRESOLVED = "unresolved"


class AnchorAddress(BaseModel):
    address_type: AnchorAddressType
    block_id: str | None = None
    char_range: CharRange | None = None
    strategy: str | None = None


class AnchorResolution(BaseModel):
    source_instruction_version_id: str
    target_instruction_version_id: str
    resolution_state: AnchorResolutionState
    trace: dict[str, object] | None = None


class ScreenshotAsset(BaseModel):
    id: str
    anchor_id: str
    version: int = Field(ge=1)
    kind: ScreenshotAssetKind
    previous_asset_id: str | None = None
    image_uri: str
    mime_type: ScreenshotMimeType
    width: int
    height: int
    extraction_key: str | None = None
    checksum_sha256: str | None = None
    upload_id: str | None = None
    ops_hash: str | None = None
    rendered_from_asset_id: str | None = None
    is_deleted: bool
    created_at: datetime


class ScreenshotAnchor(BaseModel):
    id: str
    instruction_id: str
    instruction_version_id: str
    addressing: AnchorAddress
    active_asset_id: str | None
    assets: list[ScreenshotAsset] | None = None
    resolution: AnchorResolution | None = None
    created_at: datetime
    updated_at: datetime


class ScreenshotExtractionRequest(BaseModel):
    instruction_id: str
    instruction_version_id: str
    anchor_id: str | None = None
    block_id: str | None = None
    char_range: CharRange | None = None
    timestamp_ms: int
    offset_ms: int = Field(default=0)
    strategy: ScreenshotStrategy = Field(default=ScreenshotStrategy.PRECISE)
    format: ScreenshotFormat = Field(default=ScreenshotFormat.PNG)
    idempotency_key: str | None = None


class ScreenshotAnchorCreateRequest(BaseModel):
    instruction_version_id: str
    addressing: AnchorAddress


class ScreenshotReplaceRequest(BaseModel):
    instruction_version_id: str
    timestamp_ms: int
    offset_ms: int = Field(default=0)
    strategy: ScreenshotStrategy = Field(default=ScreenshotStrategy.PRECISE)
    format: ScreenshotFormat = Field(default=ScreenshotFormat.PNG)
    idempotency_key: str | None = None


class AnnotationOperationType(str, Enum):
    BLUR = "blur"
    ARROW = "arrow"
    MARKER = "marker"
    PENCIL = "pencil"


class AnnotationOperation(BaseModel):
    op_type: AnnotationOperationType
    geometry: dict[str, object]
    style: dict[str, object]


class AnnotateScreenshotRequest(BaseModel):
    base_asset_id: str
    operations: list[AnnotationOperation] = Field(min_length=1)
    idempotency_key: str | None = None


class AnnotateScreenshotResponse(BaseModel):
    anchor_id: str
    base_asset_id: str
    ops_hash: str
    rendered_asset_id: str
    active_asset_id: str


class SoftDeleteScreenshotAssetResponse(BaseModel):
    anchor_id: str
    deleted_asset_id: str
    active_asset_id: str | None


class CreateCustomUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: ScreenshotMimeType
    size_bytes: int = Field(ge=1)
    checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


class CustomUploadTicket(BaseModel):
    upload_id: str
    upload_url: str
    expires_at: datetime
    max_size_bytes: int
    allowed_mime_types: list[ScreenshotMimeType]


class ConfirmCustomUploadRequest(BaseModel):
    mime_type: ScreenshotMimeType
    size_bytes: int = Field(ge=1)
    checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class ConfirmCustomUploadResponse(BaseModel):
    asset: ScreenshotAsset


class AttachUploadedAssetRequest(BaseModel):
    upload_id: str
    instruction_version_id: str
    idempotency_key: str | None = None
