import type { ApiClient } from "@/shared/api/client";

export type JobStatus =
  | "CREATED"
  | "UPLOADING"
  | "UPLOADED"
  | "AUDIO_EXTRACTING"
  | "AUDIO_READY"
  | "TRANSCRIBING"
  | "TRANSCRIPT_READY"
  | "GENERATING"
  | "DRAFT_READY"
  | "EDITING"
  | "REGENERATING"
  | "EXPORTING"
  | "DONE"
  | "FAILED"
  | "CANCELLED";

export interface ArtifactManifest {
  audio_uri?: string;
  draft_uri?: string;
  exports?: string[];
  transcript_uri?: string;
  video_uri?: string;
}

export interface Job {
  created_at: string;
  id: string;
  manifest?: ArtifactManifest;
  project_id: string;
  status: JobStatus;
  updated_at?: string;
}

export interface TranscriptSegment {
  end_ms: number;
  start_ms: number;
  text: string;
}

export interface TranscriptPage {
  items: TranscriptSegment[];
  limit: number;
  next_cursor?: string | null;
}

export interface ConfirmUploadRequest {
  video_uri: string;
}

export interface ConfirmUploadResponse {
  job: Job;
  replayed: boolean;
}

export interface RunJobResponse {
  dispatch_id: string;
  job_id: string;
  replayed: boolean;
  status: JobStatus;
}

export interface RetryJobRequest {
  client_request_id: string;
  model_profile: string;
}

export interface RetryJobResponse {
  checkpoint_ref: string;
  dispatch_id: string;
  job_id: string;
  model_profile: string;
  replayed: boolean;
  resume_from_status: JobStatus;
  status: JobStatus;
}

export interface TranscriptNotReadyDetails {
  current_status: JobStatus;
}

function buildTranscriptPath(
  jobId: string,
  options: {
    cursor?: string;
    limit?: number;
  } = {},
): string {
  const encodedJobId = encodeURIComponent(jobId);
  const searchParams = new URLSearchParams();

  if (options.limit !== undefined) {
    searchParams.set("limit", String(options.limit));
  }

  if (options.cursor) {
    searchParams.set("cursor", options.cursor);
  }

  const query = searchParams.toString();
  return query ? `/jobs/${encodedJobId}/transcript?${query}` : `/jobs/${encodedJobId}/transcript`;
}

export async function createJob(apiClient: ApiClient, projectId: string): Promise<Job> {
  return apiClient.post<Job>(`/projects/${projectId}/jobs`, null, { auth: "required" });
}

export async function getJob(apiClient: ApiClient, jobId: string): Promise<Job> {
  return apiClient.get<Job>(`/jobs/${jobId}`, { auth: "required" });
}

export async function getJobTranscript(
  apiClient: ApiClient,
  jobId: string,
  options: {
    cursor?: string;
    limit?: number;
  } = {},
): Promise<TranscriptPage> {
  return apiClient.get<TranscriptPage>(buildTranscriptPath(jobId, options), { auth: "required" });
}

export async function confirmJobUpload(
  apiClient: ApiClient,
  jobId: string,
  payload: ConfirmUploadRequest,
): Promise<ConfirmUploadResponse> {
  return apiClient.post<ConfirmUploadResponse>(
    `/jobs/${jobId}/confirm-upload`,
    { video_uri: payload.video_uri },
    { auth: "required" },
  );
}

export async function runJob(apiClient: ApiClient, jobId: string): Promise<RunJobResponse> {
  return apiClient.post<RunJobResponse>(`/jobs/${jobId}/run`, null, { auth: "required" });
}

export async function retryJob(
  apiClient: ApiClient,
  jobId: string,
  payload: RetryJobRequest,
): Promise<RetryJobResponse> {
  return apiClient.post<RetryJobResponse>(
    `/jobs/${jobId}/retry`,
    {
      client_request_id: payload.client_request_id,
      model_profile: payload.model_profile,
    },
    { auth: "required" },
  );
}

export async function cancelJob(apiClient: ApiClient, jobId: string): Promise<Job> {
  return apiClient.post<Job>(`/jobs/${jobId}/cancel`, null, { auth: "required" });
}

export function parseTranscriptNotReadyDetails(details: unknown): TranscriptNotReadyDetails | null {
  if (typeof details !== "object" || details === null) {
    return null;
  }

  const candidate = details as Record<string, unknown>;
  if (typeof candidate.current_status !== "string") {
    return null;
  }

  return {
    current_status: candidate.current_status as JobStatus,
  };
}
