"""Instruction service layer."""

from dataclasses import dataclass

from app.errors import ApiError
from app.repositories.memory import InMemoryStore, InstructionRecord, RegenerateTaskRecord
from app.schemas.instruction import Instruction, RegenerateRequest, RegenerateTask


@dataclass(slots=True)
class RegenerateRequestResult:
    task: RegenerateTask
    replayed: bool


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
            model_profile_id=current_record.model_profile_id,
            prompt_template_id=current_record.prompt_template_id,
            prompt_params_ref=current_record.prompt_params_ref,
        )
        return self._to_instruction(updated_record)

    def request_regenerate(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        payload: RegenerateRequest,
    ) -> RegenerateRequestResult:
        current_record = self._store.get_instruction_for_owner(
            owner_id=owner_id,
            instruction_id=instruction_id,
            version=None,
        )
        if current_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        existing_task = self._store.get_regenerate_task_for_request(
            owner_id=owner_id,
            instruction_id=instruction_id,
            client_request_id=payload.client_request_id,
        )
        if existing_task is not None:
            if not self._store.regenerate_payload_matches_task(
                task=existing_task,
                base_version=payload.base_version,
                selection=payload.selection,
                context=payload.context,
                model_profile=payload.model_profile,
                prompt_template_id=payload.prompt_template_id,
                prompt_params_ref=payload.prompt_params_ref,
            ):
                raise ApiError(
                    status_code=400,
                    code="VALIDATION_ERROR",
                    message="Duplicate client_request_id payload differs from first accepted request.",
                )
            task = self._to_regenerate_task(existing_task, replayed=True)
            return RegenerateRequestResult(task=task, replayed=True)

        if current_record.version != payload.base_version:
            raise ApiError(
                status_code=409,
                code="VERSION_CONFLICT",
                message="Instruction base version does not match current version.",
                details={
                    "base_version": payload.base_version,
                    "current_version": current_record.version,
                },
            )

        try:
            task_record, replayed = self._store.create_regenerate_task(
                owner_id=owner_id,
                instruction_id=instruction_id,
                job_id=current_record.job_id,
                base_version=payload.base_version,
                selection=payload.selection,
                client_request_id=payload.client_request_id,
                context=payload.context,
                model_profile=payload.model_profile,
                prompt_template_id=payload.prompt_template_id,
                prompt_params_ref=payload.prompt_params_ref,
            )
        except ValueError as exc:
            raise ApiError(
                status_code=400,
                code="VALIDATION_ERROR",
                message="Invalid regenerate payload",
            ) from exc

        task = self._to_regenerate_task(task_record, replayed=replayed)
        return RegenerateRequestResult(task=task, replayed=replayed)

    def get_regenerate_task(
        self,
        *,
        owner_id: str,
        task_id: str,
    ) -> RegenerateTask:
        record = self._store.get_regenerate_task_for_owner(owner_id=owner_id, task_id=task_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
        return self._to_regenerate_task(record, replayed=False)

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

    @staticmethod
    def _to_regenerate_task(record: RegenerateTaskRecord, *, replayed: bool) -> RegenerateTask:
        return RegenerateTask(
            id=record.id,
            status=record.status,
            progress_pct=record.progress_pct,
            instruction_id=record.instruction_id,
            instruction_version=record.instruction_version,
            failure_code=record.failure_code,
            failure_message=record.failure_message,
            failed_stage=record.failed_stage,
            provenance=record.provenance.model_copy(deep=True),
            replayed=replayed,
            requested_at=record.requested_at,
            updated_at=record.updated_at,
        )
