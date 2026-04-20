import type { ApiClient } from "@/shared/api/client";

export type ValidationStatus = "PASS" | "FAIL";

export interface ValidationIssue {
  code: string;
  message: string;
  path?: string | null;
}

export interface Instruction {
  id?: string | null;
  instruction_id: string;
  job_id: string;
  markdown: string;
  model_profile_id?: string | null;
  prompt_params_ref?: string | null;
  prompt_template_id?: string | null;
  updated_at: string;
  validated_at?: string | null;
  validation_errors?: ValidationIssue[] | null;
  validation_status: ValidationStatus;
  validator_version?: string | null;
  version: number;
}

export interface UpdateInstructionInput {
  base_version: number;
  markdown: string;
}

export interface RegenerateCharRange {
  end_offset: number;
  start_offset: number;
}

export interface RegenerateSelection {
  block_id?: string;
  char_range?: RegenerateCharRange;
}

export interface RegenerateRequestInput {
  base_version: number;
  client_request_id: string;
  context?: string;
  model_profile?: string;
  prompt_params_ref?: string;
  prompt_template_id?: string;
  selection: RegenerateSelection;
}

export interface RegenerateProvenance {
  base_version: number;
  instruction_id: string;
  model_profile?: string | null;
  prompt_params_ref?: string | null;
  prompt_template_id?: string | null;
  requested_at: string;
  requested_by: string;
  selection: RegenerateSelection;
}

export type RegenerateTaskStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";

export interface RegenerateTask {
  failed_stage?: string | null;
  failure_code?: string | null;
  failure_message?: string | null;
  id: string;
  instruction_id?: string | null;
  instruction_version?: number | null;
  progress_pct?: number | null;
  provenance?: RegenerateProvenance | null;
  replayed?: boolean;
  requested_at: string;
  status: RegenerateTaskStatus;
  updated_at?: string | null;
}

export interface VersionConflictDetails {
  base_version: number;
  current_version: number;
}

function buildInstructionPath(instructionId: string, version?: number): string {
  const encodedInstructionId = encodeURIComponent(instructionId);
  if (version === undefined) {
    return `/instructions/${encodedInstructionId}`;
  }

  return `/instructions/${encodedInstructionId}?version=${version}`;
}

export async function getInstruction(
  apiClient: ApiClient,
  instructionId: string,
  options: { version?: number } = {},
): Promise<Instruction> {
  return apiClient.get<Instruction>(buildInstructionPath(instructionId, options.version), {
    auth: "required",
  });
}

export async function updateInstruction(
  apiClient: ApiClient,
  instructionId: string,
  input: UpdateInstructionInput,
): Promise<Instruction> {
  return apiClient.request<Instruction>(buildInstructionPath(instructionId), {
    auth: "required",
    body: {
      base_version: input.base_version,
      markdown: input.markdown,
    },
    method: "PUT",
  });
}

export async function requestInstructionRegenerate(
  apiClient: ApiClient,
  instructionId: string,
  input: RegenerateRequestInput,
): Promise<RegenerateTask> {
  return apiClient.post<RegenerateTask>(
    `${buildInstructionPath(instructionId)}/regenerate`,
    {
      base_version: input.base_version,
      client_request_id: input.client_request_id,
      context: input.context,
      model_profile: input.model_profile,
      prompt_params_ref: input.prompt_params_ref,
      prompt_template_id: input.prompt_template_id,
      selection: input.selection,
    },
    { auth: "required" },
  );
}

export async function getRegenerateTask(apiClient: ApiClient, taskId: string): Promise<RegenerateTask> {
  return apiClient.get<RegenerateTask>(`/tasks/${encodeURIComponent(taskId)}`, { auth: "required" });
}

export function parseVersionConflictDetails(details: unknown): VersionConflictDetails | null {
  if (typeof details !== "object" || details === null) {
    return null;
  }

  const candidate = details as Record<string, unknown>;
  if (
    typeof candidate.base_version !== "number" ||
    !Number.isInteger(candidate.base_version) ||
    typeof candidate.current_version !== "number" ||
    !Number.isInteger(candidate.current_version)
  ) {
    return null;
  }

  return {
    base_version: candidate.base_version,
    current_version: candidate.current_version,
  };
}

export function isRegenerateTaskTerminal(status: RegenerateTaskStatus): boolean {
  return status === "SUCCEEDED" || status === "FAILED";
}
