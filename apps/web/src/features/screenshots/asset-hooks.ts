"use client";

import { useCallback, useEffect, useState } from "react";

import { useApiClient } from "@/shared/providers/app-providers";
import { useBoundedPolling } from "@/shared/hooks/use-bounded-polling";
import {
  annotateScreenshot,
  attachUploadedAsset,
  confirmCustomUpload,
  createCustomUploadTicket,
  getScreenshotTask,
  isScreenshotTaskTerminal,
  requestScreenshotReplacement,
  softDeleteScreenshotAsset,
  type AnnotateScreenshotRequestInput,
  type AnnotateScreenshotResponse,
  type ScreenshotReplaceRequestInput,
  type ScreenshotTask,
} from "@/features/screenshots/api";
import {
  computeBlobSha256,
  describeAnnotatedScreenshot,
  describeAssetLifecycleError,
  describeAttachedUpload,
  describeSoftDeletedAsset,
  normalizeScreenshotUploadMimeType,
  readImageDimensions,
  uploadFileToSignedUrl,
} from "@/features/screenshots/asset-lifecycle";
import type { AnchorAssetPreview } from "@/features/screenshots/anchors";
import {
  describeScreenshotTask,
  type ScreenshotFeedback,
} from "@/features/screenshots/extraction";

export interface ScreenshotAssetLifecycleState {
  annotationFeedback: ScreenshotFeedback | null;
  annotationIsSubmitting: boolean;
  annotationLastIdempotencyKey: string | null;
  annotationResult: AnnotateScreenshotResponse | null;
  assetPreview: AnchorAssetPreview | null;
  deleteAsset: (input: { anchorId: string; assetId: string }) => Promise<void>;
  deleteFeedback: ScreenshotFeedback | null;
  dismissAnnotationFeedback: () => void;
  dismissDeleteFeedback: () => void;
  dismissReplaceFeedback: () => void;
  dismissUploadFeedback: () => void;
  pendingDeleteAssetId: string | null;
  refreshReplaceTask: () => Promise<void>;
  replaceFeedback: ScreenshotFeedback | null;
  replaceIsSubmitting: boolean;
  replaceLastIdempotencyKey: string | null;
  replacePolling: ReturnType<typeof useBoundedPolling>["polling"];
  replaceTask: ScreenshotTask | null;
  stopReplacePolling: () => void;
  submitAnnotation: (input: {
    anchorId: string;
    payload: AnnotateScreenshotRequestInput;
    previousActiveAssetId: string | null;
  }) => Promise<boolean>;
  submitReplace: (input: { anchorId: string; payload: ScreenshotReplaceRequestInput }) => Promise<void>;
  submitUploadAndAttach: (input: {
    anchorId: string;
    attachInstructionVersionId: string;
    file: File;
    idempotencyKey: string;
    jobId: string;
  }) => Promise<boolean>;
  uploadFeedback: ScreenshotFeedback | null;
  uploadIsSubmitting: boolean;
  uploadLastIdempotencyKey: string | null;
}

export function useScreenshotAssetLifecycle({
  onAssetStateChanged,
  scopeKey,
}: {
  onAssetStateChanged?: () => void;
  scopeKey: string;
}): ScreenshotAssetLifecycleState {
  const apiClient = useApiClient();
  const [annotationResult, setAnnotationResult] = useState<AnnotateScreenshotResponse | null>(null);
  const [annotationFeedback, setAnnotationFeedback] = useState<ScreenshotFeedback | null>(null);
  const [annotationIsSubmitting, setAnnotationIsSubmitting] = useState(false);
  const [annotationLastIdempotencyKey, setAnnotationLastIdempotencyKey] = useState<string | null>(null);
  const [assetPreview, setAssetPreview] = useState<AnchorAssetPreview | null>(null);
  const [replaceTask, setReplaceTask] = useState<ScreenshotTask | null>(null);
  const [replaceFeedback, setReplaceFeedback] = useState<ScreenshotFeedback | null>(null);
  const [replaceIsSubmitting, setReplaceIsSubmitting] = useState(false);
  const [replaceLastIdempotencyKey, setReplaceLastIdempotencyKey] = useState<string | null>(null);
  const [uploadFeedback, setUploadFeedback] = useState<ScreenshotFeedback | null>(null);
  const [uploadIsSubmitting, setUploadIsSubmitting] = useState(false);
  const [uploadLastIdempotencyKey, setUploadLastIdempotencyKey] = useState<string | null>(null);
  const [deleteFeedback, setDeleteFeedback] = useState<ScreenshotFeedback | null>(null);
  const [pendingDeleteAssetId, setPendingDeleteAssetId] = useState<string | null>(null);

  const refreshAnchorState = useCallback(() => {
    onAssetStateChanged?.();
  }, [onAssetStateChanged]);

  const refreshTask = useCallback(
    async (taskId: string) => {
      const nextTask = await getScreenshotTask(apiClient, taskId);
      setReplaceTask((current) => ({
        ...nextTask,
        replayed: current?.replayed && current.task_id === nextTask.task_id ? current.replayed : nextTask.replayed,
      }));

      if (isScreenshotTaskTerminal(nextTask.status)) {
        setReplaceFeedback(describeScreenshotTask(nextTask));
        if (nextTask.status === "SUCCEEDED" && nextTask.anchor_id) {
          setAssetPreview({
            active_asset_id: nextTask.asset_id ?? null,
            anchor_id: nextTask.anchor_id,
          });
          refreshAnchorState();
        }
      }

      return nextTask;
    },
    [apiClient, refreshAnchorState],
  );

  const { polling, startPolling, stopPolling } = useBoundedPolling({
    onPoll: () => {
      if (!replaceTask?.task_id) {
        return;
      }

      void refreshTask(replaceTask.task_id)
        .then((nextTask) => {
          if (isScreenshotTaskTerminal(nextTask.status)) {
            stopPolling();
          }
        })
        .catch((error) => {
          setReplaceFeedback(describeAssetLifecycleError(error, "replace"));
          stopPolling();
        });
    },
  });

  useEffect(() => {
    if (!polling.active && polling.startedAt && polling.attemptsRemaining <= 0 && replaceTask !== null) {
      setReplaceFeedback({
        description:
          "Polling stopped after the bounded retry window. Refresh task status manually to continue tracking this screenshot replacement.",
        title: "Polling paused",
        tone: "warning",
      });
    }
  }, [polling.active, polling.attemptsRemaining, polling.startedAt, replaceTask]);

  useEffect(() => {
    setAnnotationResult(null);
    setAnnotationFeedback(null);
    setAnnotationIsSubmitting(false);
    setAnnotationLastIdempotencyKey(null);
    setAssetPreview(null);
    setReplaceTask(null);
    setReplaceFeedback(null);
    setReplaceIsSubmitting(false);
    setReplaceLastIdempotencyKey(null);
    setUploadFeedback(null);
    setUploadIsSubmitting(false);
    setUploadLastIdempotencyKey(null);
    setDeleteFeedback(null);
    setPendingDeleteAssetId(null);
    stopPolling();
  }, [scopeKey, stopPolling]);

  const submitAnnotation = useCallback(
    async ({
      anchorId,
      payload,
      previousActiveAssetId,
    }: {
      anchorId: string;
      payload: AnnotateScreenshotRequestInput;
      previousActiveAssetId: string | null;
    }) => {
      try {
        setAnnotationIsSubmitting(true);
        setAnnotationFeedback(null);
        setAnnotationLastIdempotencyKey(payload.idempotency_key ?? null);

        const response = await annotateScreenshot(apiClient, anchorId, payload);
        setAnnotationResult(response);
        setAssetPreview({
          active_asset_id: response.active_asset_id,
          anchor_id: response.anchor_id,
        });
        setAnnotationFeedback(describeAnnotatedScreenshot(response, previousActiveAssetId));
        refreshAnchorState();
        return true;
      } catch (error) {
        setAnnotationFeedback(describeAssetLifecycleError(error, "annotate"));
        return false;
      } finally {
        setAnnotationIsSubmitting(false);
      }
    },
    [apiClient, refreshAnchorState],
  );

  const submitReplace = useCallback(
    async ({ anchorId, payload }: { anchorId: string; payload: ScreenshotReplaceRequestInput }) => {
      try {
        setReplaceIsSubmitting(true);
        setReplaceFeedback(null);
        setReplaceLastIdempotencyKey(payload.idempotency_key ?? null);

        const previousTaskId = replaceTask?.task_id ?? null;
        const nextTask = await requestScreenshotReplacement(apiClient, anchorId, payload);
        const normalizedTask =
          previousTaskId !== null && previousTaskId === nextTask.task_id
            ? { ...nextTask, replayed: true }
            : nextTask;

        setReplaceTask(normalizedTask);
        setReplaceFeedback(describeScreenshotTask(normalizedTask));

        if (isScreenshotTaskTerminal(normalizedTask.status)) {
          stopPolling();
          if (normalizedTask.status === "SUCCEEDED" && normalizedTask.anchor_id) {
            setAssetPreview({
              active_asset_id: normalizedTask.asset_id ?? null,
              anchor_id: normalizedTask.anchor_id,
            });
            refreshAnchorState();
          }
          return;
        }

        startPolling({
          intervalMs: 2500,
          maxAttempts: 10,
          reason: "screenshot-replace-task-status",
          watchValue: normalizedTask.task_id,
        });
      } catch (error) {
        setReplaceFeedback(describeAssetLifecycleError(error, "replace"));
      } finally {
        setReplaceIsSubmitting(false);
      }
    },
    [apiClient, refreshAnchorState, replaceTask?.task_id, startPolling, stopPolling],
  );

  const refreshReplaceTask = useCallback(async () => {
    if (!replaceTask?.task_id) {
      return;
    }

    try {
      const nextTask = await refreshTask(replaceTask.task_id);
      if (isScreenshotTaskTerminal(nextTask.status)) {
        stopPolling();
      }
    } catch (error) {
      setReplaceFeedback(describeAssetLifecycleError(error, "replace"));
    }
  }, [refreshTask, replaceTask?.task_id, stopPolling]);

  const submitUploadAndAttach = useCallback(
    async ({
      anchorId,
      attachInstructionVersionId,
      file,
      idempotencyKey,
      jobId,
    }: {
      anchorId: string;
      attachInstructionVersionId: string;
      file: File;
      idempotencyKey: string;
      jobId: string;
    }) => {
      try {
        setUploadIsSubmitting(true);
        setUploadFeedback(null);
        setUploadLastIdempotencyKey(idempotencyKey);

        const mimeType = normalizeScreenshotUploadMimeType(file.type);
        if (!mimeType) {
          throw new Error("Only PNG, JPEG, and WebP uploads are supported.");
        }

        const [checksumSha256, dimensions] = await Promise.all([
          computeBlobSha256(file),
          readImageDimensions(file),
        ]);

        const ticket = await createCustomUploadTicket(apiClient, jobId, {
          checksum_sha256: checksumSha256,
          filename: file.name || "custom-screenshot",
          mime_type: mimeType,
          size_bytes: file.size,
        });

        await uploadFileToSignedUrl(ticket.upload_url, file, mimeType);

        await confirmCustomUpload(apiClient, jobId, ticket.upload_id, {
          checksum_sha256: checksumSha256,
          height: dimensions.height,
          mime_type: mimeType,
          size_bytes: file.size,
          width: dimensions.width,
        });

        const attachedAnchor = await attachUploadedAsset(apiClient, anchorId, {
          idempotency_key: idempotencyKey,
          instruction_version_id: attachInstructionVersionId,
          upload_id: ticket.upload_id,
        });

        setAssetPreview({
          active_asset_id: attachedAnchor.active_asset_id,
          anchor_id: attachedAnchor.id,
        });
        setUploadFeedback(describeAttachedUpload(attachedAnchor));
        refreshAnchorState();
        return true;
      } catch (error) {
        setUploadFeedback(describeAssetLifecycleError(error, "upload"));
        return false;
      } finally {
        setUploadIsSubmitting(false);
      }
    },
    [apiClient, refreshAnchorState],
  );

  const deleteAsset = useCallback(
    async ({ anchorId, assetId }: { anchorId: string; assetId: string }) => {
      try {
        setPendingDeleteAssetId(assetId);
        setDeleteFeedback(null);

        const response = await softDeleteScreenshotAsset(apiClient, anchorId, assetId);
        setAssetPreview({
          active_asset_id: response.active_asset_id,
          anchor_id: response.anchor_id,
          deleted_asset_id: response.deleted_asset_id,
        });
        setDeleteFeedback(describeSoftDeletedAsset(response));
        refreshAnchorState();
      } catch (error) {
        setDeleteFeedback(describeAssetLifecycleError(error, "delete"));
      } finally {
        setPendingDeleteAssetId(null);
      }
    },
    [apiClient, refreshAnchorState],
  );

  return {
    annotationFeedback,
    annotationIsSubmitting,
    annotationLastIdempotencyKey,
    annotationResult,
    assetPreview,
    deleteAsset,
    deleteFeedback,
    dismissAnnotationFeedback() {
      setAnnotationFeedback(null);
    },
    dismissDeleteFeedback() {
      setDeleteFeedback(null);
    },
    dismissReplaceFeedback() {
      setReplaceFeedback(null);
    },
    dismissUploadFeedback() {
      setUploadFeedback(null);
    },
    pendingDeleteAssetId,
    refreshReplaceTask,
    replaceFeedback,
    replaceIsSubmitting,
    replaceLastIdempotencyKey,
    replacePolling: polling,
    replaceTask,
    stopReplacePolling: stopPolling,
    submitAnnotation,
    submitReplace,
    submitUploadAndAttach,
    uploadFeedback,
    uploadIsSubmitting,
    uploadLastIdempotencyKey,
  };
}
