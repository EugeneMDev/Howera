import React from "react";

import { StatusPill } from "@/shared/ui/status-pill";
import type { JobStatus } from "@/features/jobs/api";

function getJobStatusTone(status: JobStatus) {
  switch (status) {
    case "DONE":
    case "DRAFT_READY":
    case "TRANSCRIPT_READY":
    case "AUDIO_READY":
      return "success";
    case "FAILED":
    case "CANCELLED":
      return "danger";
    case "UPLOADING":
    case "UPLOADED":
    case "AUDIO_EXTRACTING":
    case "TRANSCRIBING":
    case "GENERATING":
    case "REGENERATING":
    case "EXPORTING":
      return "warning";
    case "CREATED":
    case "EDITING":
    default:
      return "neutral";
  }
}

interface JobStatusBadgeProps {
  status: JobStatus;
}

export function JobStatusBadge({ status }: JobStatusBadgeProps) {
  return <StatusPill tone={getJobStatusTone(status)}>{status}</StatusPill>;
}
