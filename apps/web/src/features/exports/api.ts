import type { ApiClient } from "@/shared/api/client";

export type ExportFormat = "PDF" | "MD_ZIP";
export type ExportStatus = "REQUESTED" | "RUNNING" | "SUCCEEDED" | "FAILED";
export type ExportAuditEventType =
  | "EXPORT_REQUESTED"
  | "EXPORT_STARTED"
  | "EXPORT_SUCCEEDED"
  | "EXPORT_FAILED";

export interface CreateExportRequestInput {
  format: ExportFormat;
  idempotency_key?: string;
  instruction_version_id: string;
}

export interface ExportAnchorBinding {
  active_asset_id: string;
  anchor_id: string;
  rendered_asset_id?: string | null;
}

export interface ExportProvenance {
  anchors: ExportAnchorBinding[];
  generated_at?: string | null;
  instruction_snapshot_id: string;
  instruction_version_id: string;
  model_profile_id: string;
  prompt_params_ref?: string | null;
  prompt_template_id: string;
  screenshot_set_hash: string;
}

export interface ExportRecord {
  created_at: string;
  download_url?: string | null;
  download_url_expires_at?: string | null;
  format: ExportFormat;
  id: string;
  identity_key: string;
  instruction_version_id: string;
  job_id: string;
  last_audit_event?: ExportAuditEventType | null;
  provenance?: ExportProvenance | null;
  provenance_frozen_at?: string | null;
  replayed?: boolean;
  screenshot_set_hash: string;
  status: ExportStatus;
  updated_at: string;
}

export async function requestExport(
  apiClient: ApiClient,
  jobId: string,
  input: CreateExportRequestInput,
): Promise<ExportRecord> {
  const path = `/jobs/${encodeURIComponent(jobId)}/exports`;
  const body = {
    format: input.format,
    idempotency_key: input.idempotency_key,
    instruction_version_id: input.instruction_version_id,
  };

  if (apiClient.requestWithMeta) {
    const response = await apiClient.requestWithMeta<ExportRecord>(path, {
      auth: "required",
      body,
      method: "POST",
    });

    return {
      ...response.data,
      replayed: response.status === 200,
    };
  }

  const record = await apiClient.request<ExportRecord>(path, {
    auth: "required",
    body,
    method: "POST",
  });

  return {
    ...record,
    replayed: false,
  };
}

export async function getExport(apiClient: ApiClient, exportId: string): Promise<ExportRecord> {
  return apiClient.get<ExportRecord>(`/exports/${encodeURIComponent(exportId)}`, {
    auth: "required",
  });
}

export function isExportTerminal(status: ExportStatus): boolean {
  return status === "SUCCEEDED" || status === "FAILED";
}
