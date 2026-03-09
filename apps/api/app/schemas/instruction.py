"""Instruction API schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class ValidationIssue(BaseModel):
    code: str
    message: str
    path: str | None = None


class Instruction(BaseModel):
    instruction_id: str
    id: str | None = Field(default=None, deprecated=True, description="Deprecated alias of instruction_id.")
    job_id: str
    version: int
    markdown: str
    updated_at: datetime
    validation_status: ValidationStatus
    validation_errors: list[ValidationIssue] | None = None
    validated_at: datetime | None = None
    validator_version: str | None = None
    model_profile_id: str | None = None
    prompt_template_id: str | None = None
    prompt_params_ref: str | None = None


class UpdateInstructionRequest(BaseModel):
    base_version: int = Field(ge=1)
    markdown: str


class CharRange(BaseModel):
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)


class RegenerateSelection(BaseModel):
    block_id: str | None = None
    char_range: CharRange | None = None

    @model_validator(mode="after")
    def _validate_exactly_one_selector(self) -> "RegenerateSelection":
        has_block_id = self.block_id is not None
        has_char_range = self.char_range is not None
        if has_block_id == has_char_range:
            raise ValueError("Selection must include block_id or char_range.")
        return self


class RegenerateRequest(BaseModel):
    base_version: int = Field(ge=1)
    selection: RegenerateSelection
    context: str | None = None
    client_request_id: str
    model_profile: str | None = None
    prompt_template_id: str | None = None
    prompt_params_ref: str | None = None


class RegenerateProvenance(BaseModel):
    instruction_id: str
    base_version: int
    selection: RegenerateSelection
    requested_by: str
    requested_at: datetime
    model_profile: str | None = None
    prompt_template_id: str | None = None
    prompt_params_ref: str | None = None


class RegenerateTaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class RegenerateTask(BaseModel):
    id: str
    status: RegenerateTaskStatus
    progress_pct: int | None = Field(default=None, ge=0, le=100)
    instruction_id: str | None = None
    instruction_version: int | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failed_stage: str | None = None
    provenance: RegenerateProvenance | None = None
    replayed: bool = False
    requested_at: datetime
    updated_at: datetime | None = None
