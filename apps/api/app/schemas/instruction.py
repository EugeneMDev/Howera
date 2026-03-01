"""Instruction API schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


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
