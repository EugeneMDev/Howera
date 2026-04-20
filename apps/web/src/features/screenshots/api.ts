import type { ApiClient } from "@/shared/api/client";

export type ScreenshotOperation = "extract" | "replace";
export type ScreenshotTaskStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";
export type ScreenshotStrategy = "nearest_keyframe" | "precise";
export type ScreenshotFormat = "png" | "jpg" | "webp";
export type AnchorAddressType = "block_id" | "char_range";
export type AnchorResolutionState = "retain" | "remap" | "unresolved";
export type ScreenshotAssetKind = "EXTRACTED" | "UPLOADED" | "ANNOTATED";
export type ScreenshotMimeType = "image/png" | "image/jpeg" | "image/webp";
export type AnnotationOperationType = "blur" | "arrow" | "marker" | "pencil";

export interface ScreenshotCharRange {
  end_offset: number;
  start_offset: number;
}

export interface AnchorAddress {
  address_type: AnchorAddressType;
  block_id?: string | null;
  char_range?: ScreenshotCharRange | null;
  strategy?: string | null;
}

export interface AnchorResolution {
  resolution_state: AnchorResolutionState;
  source_instruction_version_id: string;
  target_instruction_version_id: string;
  trace?: Record<string, unknown> | null;
}

export interface ScreenshotAsset {
  anchor_id: string;
  checksum_sha256?: string | null;
  created_at: string;
  extraction_key?: string | null;
  height: number;
  id: string;
  image_uri: string;
  is_deleted: boolean;
  kind: ScreenshotAssetKind;
  mime_type: ScreenshotMimeType;
  ops_hash?: string | null;
  previous_asset_id?: string | null;
  rendered_from_asset_id?: string | null;
  upload_id?: string | null;
  version: number;
  width: number;
}

export interface ScreenshotAnchor {
  active_asset_id: string | null;
  addressing: AnchorAddress;
  assets?: ScreenshotAsset[] | null;
  created_at: string;
  id: string;
  instruction_id: string;
  instruction_version_id: string;
  resolution?: AnchorResolution | null;
  updated_at: string;
}

export interface ScreenshotTask {
  anchor_id?: string | null;
  asset_id?: string | null;
  failure_code?: string | null;
  failure_message?: string | null;
  operation: ScreenshotOperation;
  replayed?: boolean;
  status: ScreenshotTaskStatus;
  task_id: string;
}

export interface ScreenshotExtractionRequestInput {
  anchor_id?: string;
  block_id?: string;
  char_range?: ScreenshotCharRange;
  format?: ScreenshotFormat;
  idempotency_key?: string;
  instruction_id: string;
  instruction_version_id: string;
  offset_ms?: number;
  strategy?: ScreenshotStrategy;
  timestamp_ms: number;
}

export interface ScreenshotReplaceRequestInput {
  format?: ScreenshotFormat;
  idempotency_key?: string;
  instruction_version_id: string;
  offset_ms?: number;
  strategy?: ScreenshotStrategy;
  timestamp_ms: number;
}

export interface ListScreenshotAnchorsOptions {
  include_deleted_assets?: boolean;
  instruction_version_id?: string;
}

export interface SoftDeleteScreenshotAssetResponse {
  active_asset_id: string | null;
  anchor_id: string;
  deleted_asset_id: string;
}

export interface CustomUploadTicketRequestInput {
  checksum_sha256: string;
  filename: string;
  mime_type: ScreenshotMimeType;
  size_bytes: number;
}

export interface CustomUploadTicket {
  allowed_mime_types: ScreenshotMimeType[];
  expires_at: string;
  max_size_bytes: number;
  upload_id: string;
  upload_url: string;
}

export interface ConfirmCustomUploadRequestInput {
  checksum_sha256: string;
  height: number;
  mime_type: ScreenshotMimeType;
  size_bytes: number;
  width: number;
}

export interface ConfirmCustomUploadResponse {
  asset: ScreenshotAsset;
}

export interface AttachUploadedAssetRequestInput {
  idempotency_key?: string;
  instruction_version_id: string;
  upload_id: string;
}

export interface AnnotationOperation {
  geometry: Record<string, unknown>;
  op_type: AnnotationOperationType;
  style: Record<string, unknown>;
}

export interface AnnotateScreenshotRequestInput {
  base_asset_id: string;
  idempotency_key?: string;
  operations: AnnotationOperation[];
}

export interface AnnotateScreenshotResponse {
  active_asset_id: string;
  anchor_id: string;
  base_asset_id: string;
  ops_hash: string;
  rendered_asset_id: string;
}

export async function requestScreenshotExtraction(
  apiClient: ApiClient,
  jobId: string,
  input: ScreenshotExtractionRequestInput,
): Promise<ScreenshotTask> {
  const path = `/jobs/${encodeURIComponent(jobId)}/screenshots/extract`;
  const body = {
    anchor_id: input.anchor_id,
    block_id: input.block_id,
    char_range: input.char_range,
    format: input.format,
    idempotency_key: input.idempotency_key,
    instruction_id: input.instruction_id,
    instruction_version_id: input.instruction_version_id,
    offset_ms: input.offset_ms,
    strategy: input.strategy,
    timestamp_ms: input.timestamp_ms,
  };

  if (apiClient.requestWithMeta) {
    const response = await apiClient.requestWithMeta<ScreenshotTask>(path, {
      auth: "required",
      body,
      method: "POST",
    });

    return {
      ...response.data,
      replayed: response.status === 200,
    };
  }

  return apiClient.request<ScreenshotTask>(path, {
    auth: "required",
    body,
    method: "POST",
  });
}

export async function requestScreenshotReplacement(
  apiClient: ApiClient,
  anchorId: string,
  input: ScreenshotReplaceRequestInput,
): Promise<ScreenshotTask> {
  const path = `/anchors/${encodeURIComponent(anchorId)}/replace`;
  const body = {
    format: input.format,
    idempotency_key: input.idempotency_key,
    instruction_version_id: input.instruction_version_id,
    offset_ms: input.offset_ms,
    strategy: input.strategy,
    timestamp_ms: input.timestamp_ms,
  };

  if (apiClient.requestWithMeta) {
    const response = await apiClient.requestWithMeta<ScreenshotTask>(path, {
      auth: "required",
      body,
      method: "POST",
    });

    return {
      ...response.data,
      replayed: response.status === 200,
    };
  }

  return apiClient.request<ScreenshotTask>(path, {
    auth: "required",
    body,
    method: "POST",
  });
}

export async function getScreenshotTask(apiClient: ApiClient, taskId: string): Promise<ScreenshotTask> {
  return apiClient.get<ScreenshotTask>(`/screenshot-tasks/${encodeURIComponent(taskId)}`, {
    auth: "required",
  });
}

export async function listScreenshotAnchors(
  apiClient: ApiClient,
  instructionId: string,
  options: ListScreenshotAnchorsOptions = {},
): Promise<ScreenshotAnchor[]> {
  const searchParams = new URLSearchParams();
  if (options.instruction_version_id) {
    searchParams.set("instruction_version_id", options.instruction_version_id);
  }
  if (options.include_deleted_assets !== undefined) {
    searchParams.set("include_deleted_assets", String(options.include_deleted_assets));
  }

  const queryString = searchParams.toString();
  const path = `/instructions/${encodeURIComponent(instructionId)}/anchors${queryString ? `?${queryString}` : ""}`;

  return apiClient.get<ScreenshotAnchor[]>(path, {
    auth: "required",
  });
}

export async function getScreenshotAnchor(
  apiClient: ApiClient,
  anchorId: string,
  options: { target_instruction_version_id?: string } = {},
): Promise<ScreenshotAnchor> {
  const searchParams = new URLSearchParams();
  if (options.target_instruction_version_id) {
    searchParams.set("target_instruction_version_id", options.target_instruction_version_id);
  }

  const queryString = searchParams.toString();
  const path = `/anchors/${encodeURIComponent(anchorId)}${queryString ? `?${queryString}` : ""}`;

  return apiClient.get<ScreenshotAnchor>(path, {
    auth: "required",
  });
}

export async function softDeleteScreenshotAsset(
  apiClient: ApiClient,
  anchorId: string,
  assetId: string,
): Promise<SoftDeleteScreenshotAssetResponse> {
  return apiClient.request<SoftDeleteScreenshotAssetResponse>(
    `/anchors/${encodeURIComponent(anchorId)}/assets/${encodeURIComponent(assetId)}`,
    {
      auth: "required",
      method: "DELETE",
    },
  );
}

export async function createCustomUploadTicket(
  apiClient: ApiClient,
  jobId: string,
  input: CustomUploadTicketRequestInput,
): Promise<CustomUploadTicket> {
  return apiClient.post<CustomUploadTicket>(
    `/jobs/${encodeURIComponent(jobId)}/screenshots/uploads`,
    {
      checksum_sha256: input.checksum_sha256,
      filename: input.filename,
      mime_type: input.mime_type,
      size_bytes: input.size_bytes,
    },
    {
      auth: "required",
    },
  );
}

export async function confirmCustomUpload(
  apiClient: ApiClient,
  jobId: string,
  uploadId: string,
  input: ConfirmCustomUploadRequestInput,
): Promise<ConfirmCustomUploadResponse> {
  return apiClient.post<ConfirmCustomUploadResponse>(
    `/jobs/${encodeURIComponent(jobId)}/screenshots/uploads/${encodeURIComponent(uploadId)}/confirm`,
    {
      checksum_sha256: input.checksum_sha256,
      height: input.height,
      mime_type: input.mime_type,
      size_bytes: input.size_bytes,
      width: input.width,
    },
    {
      auth: "required",
    },
  );
}

export async function attachUploadedAsset(
  apiClient: ApiClient,
  anchorId: string,
  input: AttachUploadedAssetRequestInput,
): Promise<ScreenshotAnchor> {
  return apiClient.post<ScreenshotAnchor>(
    `/anchors/${encodeURIComponent(anchorId)}/attach-upload`,
    {
      idempotency_key: input.idempotency_key,
      instruction_version_id: input.instruction_version_id,
      upload_id: input.upload_id,
    },
    {
      auth: "required",
    },
  );
}

export async function annotateScreenshot(
  apiClient: ApiClient,
  anchorId: string,
  input: AnnotateScreenshotRequestInput,
): Promise<AnnotateScreenshotResponse> {
  return apiClient.post<AnnotateScreenshotResponse>(
    `/anchors/${encodeURIComponent(anchorId)}/annotations`,
    {
      base_asset_id: input.base_asset_id,
      idempotency_key: input.idempotency_key,
      operations: input.operations,
    },
    {
      auth: "required",
    },
  );
}

export function isScreenshotTaskTerminal(status: ScreenshotTaskStatus): boolean {
  return status === "SUCCEEDED" || status === "FAILED";
}
