"""Instruction service layer."""

from app.errors import ApiError
from app.repositories.memory import InMemoryStore, InstructionRecord
from app.schemas.instruction import Instruction


class InstructionService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def get_instruction(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        version: int | None = None,
    ) -> Instruction:
        record = self._store.get_instruction_for_owner(
            owner_id=owner_id,
            instruction_id=instruction_id,
            version=version,
        )
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        return self._to_instruction(record)

    def update_instruction(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        base_version: int,
        markdown: str,
    ) -> Instruction:
        current_record = self._store.get_instruction_for_owner(
            owner_id=owner_id,
            instruction_id=instruction_id,
            version=None,
        )
        if current_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        if current_record.version != base_version:
            raise ApiError(
                status_code=409,
                code="VERSION_CONFLICT",
                message="Instruction base version does not match current version.",
                details={
                    "base_version": base_version,
                    "current_version": current_record.version,
                },
            )

        updated_record = self._store.create_instruction_version(
            owner_id=owner_id,
            instruction_id=instruction_id,
            job_id=current_record.job_id,
            version=current_record.version + 1,
            markdown=markdown,
            validation_status=current_record.validation_status,
            validation_errors=current_record.validation_errors,
            validated_at=current_record.validated_at,
            validator_version=current_record.validator_version,
            model_profile_id=current_record.model_profile_id,
            prompt_template_id=current_record.prompt_template_id,
            prompt_params_ref=current_record.prompt_params_ref,
        )
        return self._to_instruction(updated_record)

    @staticmethod
    def _to_instruction(record: InstructionRecord) -> Instruction:
        return Instruction(
            instruction_id=record.instruction_id,
            id=record.instruction_id,
            job_id=record.job_id,
            version=record.version,
            markdown=record.markdown,
            updated_at=record.updated_at,
            validation_status=record.validation_status,
            validation_errors=record.validation_errors,
            validated_at=record.validated_at,
            validator_version=record.validator_version,
            model_profile_id=record.model_profile_id,
            prompt_template_id=record.prompt_template_id,
            prompt_params_ref=record.prompt_params_ref,
        )
