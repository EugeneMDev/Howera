"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiClientError, isNoLeakNotFoundError } from "@/shared/api/errors";
import { useApiClient, useTelemetry } from "@/shared/providers/app-providers";
import {
  getInstruction,
  parseVersionConflictDetails,
  updateInstruction,
  type Instruction,
} from "@/features/instructions/api";
import {
  adoptLatestInstructionBase,
  applyInstructionSaveSuccess,
  applyInstructionVersionConflict,
  applyLoadedInstructionSnapshot,
  createInstructionEditorState,
  dismissInstructionEditorFeedback,
  isInstructionEditorDirty,
  reloadInstructionEditorFromLatest,
  updateInstructionDraft,
} from "@/features/instructions/editor-state";

type QueryStatus = "loading" | "success" | "error";
type SaveStatus = "idle" | "submitting" | "error" | "conflict";

function toErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

async function fetchLatestInstructionSnapshot(
  apiClient: ReturnType<typeof useApiClient>,
  instructionId: string,
): Promise<Instruction | null> {
  try {
    return await getInstruction(apiClient, instructionId);
  } catch {
    return null;
  }
}

export function useInstructionEditor(instructionId: string) {
  const apiClient = useApiClient();
  const telemetry = useTelemetry();
  const [editorState, setEditorState] = useState(createInstructionEditorState);
  const [status, setStatus] = useState<QueryStatus>("loading");
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [loadRevision, setLoadRevision] = useState(0);

  useEffect(() => {
    let cancelled = false;

    setStatus("loading");
    setError(null);
    setNotFound(false);

    void getInstruction(apiClient, instructionId)
      .then((instruction) => {
        if (cancelled) {
          return;
        }

        setEditorState((current) => applyLoadedInstructionSnapshot(current, instruction));
        setStatus("success");
      })
      .catch((loadError) => {
        if (cancelled) {
          return;
        }

        if (isNoLeakNotFoundError(loadError)) {
          setNotFound(true);
          setStatus("error");
          return;
        }

        setError(toErrorMessage(loadError, "Instruction could not be loaded."));
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [apiClient, instructionId, loadRevision]);

  const reload = useCallback(() => {
    setLoadRevision((current) => current + 1);
  }, []);

  return {
    conflict: editorState.conflict,
    draftMarkdown: editorState.draftMarkdown,
    error,
    feedback: editorState.feedback,
    instruction: editorState.instruction,
    isDirty: isInstructionEditorDirty(editorState),
    isSaving: saveStatus === "submitting",
    latestInstruction: editorState.latestInstruction,
    notFound,
    saveFailed:
      saveStatus === "error"
        ? editorState.feedback?.description ?? "Instruction could not be saved."
        : null,
    saveStatus,
    status,
    dismissFeedback() {
      setEditorState((current) => dismissInstructionEditorFeedback(current));
      if (saveStatus === "error" || saveStatus === "conflict") {
        setSaveStatus("idle");
      }
    },
    async saveDraft(): Promise<void> {
      if (editorState.instruction === null) {
        return;
      }

      try {
        setSaveStatus("submitting");
        setError(null);
        const updatedInstruction = await updateInstruction(apiClient, instructionId, {
          base_version: editorState.instruction.version,
          markdown: editorState.draftMarkdown,
        });
        telemetry.track({
          attributes: {
            action: "save",
            instructionId,
            instructionVersion: updatedInstruction.version,
            jobId: updatedInstruction.job_id,
            result: "succeeded",
          },
          name: "instruction.save.succeeded",
        });
        setEditorState((current) => applyInstructionSaveSuccess(current, updatedInstruction));
        setSaveStatus("idle");
      } catch (saveError) {
        if (
          saveError instanceof ApiClientError &&
          saveError.status === 409 &&
          saveError.code === "VERSION_CONFLICT"
        ) {
          const conflict = parseVersionConflictDetails(saveError.details);
          const latestInstruction = await fetchLatestInstructionSnapshot(apiClient, instructionId);

          if (conflict !== null) {
            telemetry.track({
              attributes: {
                action: "save",
                instructionId,
                instructionVersion: conflict.base_version,
                result: "conflict",
                versionConflict: `${conflict.base_version}->${conflict.current_version}`,
              },
              error: saveError,
              name: "instruction.save.conflict",
            });
            setEditorState((current) =>
              applyInstructionVersionConflict(current, conflict, latestInstruction),
            );
            setSaveStatus("conflict");
            return;
          }
        }

        telemetry.track({
          attributes: {
            action: "save",
            instructionId,
            instructionVersion: editorState.instruction.version,
            jobId: editorState.instruction.job_id,
            result: "failed",
          },
          error: saveError,
          name: "instruction.save.failed",
        });
        setEditorState((current) => ({
          ...current,
          feedback: {
            description: toErrorMessage(saveError, "Instruction could not be saved."),
            title: "Save failed",
            tone: "danger",
          },
        }));
        setSaveStatus("error");
      }
    },
    async reloadLatestIntoEditor(): Promise<void> {
      const latestInstruction = await fetchLatestInstructionSnapshot(apiClient, instructionId);
      if (latestInstruction === null) {
        setEditorState((current) => ({
          ...current,
          feedback: {
            description: "The latest instruction version could not be reloaded from the API.",
            title: "Reload failed",
            tone: "danger",
          },
        }));
        setSaveStatus("error");
        return;
      }

      setEditorState((current) =>
        reloadInstructionEditorFromLatest({
          ...current,
          latestInstruction,
        }),
      );
      setSaveStatus("idle");
    },
    setDraftMarkdown(markdown: string) {
      setEditorState((current) => updateInstructionDraft(current, markdown));
    },
    refreshLatestInstruction: reload,
    useLatestAsMergeBase() {
      setEditorState((current) => adoptLatestInstructionBase(current));
      setSaveStatus("idle");
    },
    retryLoad: reload,
  };
}
