"""Instruction markdown structural validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from app.schemas.instruction import ValidationIssue, ValidationStatus

INSTRUCTION_VALIDATOR_VERSION = "structure-v1"
_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class InstructionValidationResult:
    status: ValidationStatus
    errors: list[ValidationIssue] | None
    validated_at: datetime
    validator_version: str


def validate_instruction_markdown(markdown: str) -> InstructionValidationResult:
    """Validate minimal structural requirements for persisted instruction versions."""
    errors: list[ValidationIssue] = []
    if not markdown.strip():
        errors.append(
            ValidationIssue(
                code="STRUCTURE_EMPTY",
                message="Markdown must not be empty.",
            )
        )
    elif _HEADING_PATTERN.search(markdown) is None:
        errors.append(
            ValidationIssue(
                code="STRUCTURE_MISSING_HEADING",
                message="Markdown must include at least one heading.",
                path="heading[0]",
            )
        )

    return InstructionValidationResult(
        status=ValidationStatus.FAIL if errors else ValidationStatus.PASS,
        errors=errors or None,
        validated_at=datetime.now(UTC),
        validator_version=INSTRUCTION_VALIDATOR_VERSION,
    )


__all__ = ["INSTRUCTION_VALIDATOR_VERSION", "InstructionValidationResult", "validate_instruction_markdown"]
