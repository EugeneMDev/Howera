import { describeCommonApiError } from "@/shared/api/error-feedback";

import type {
  AnnotateScreenshotResponse,
  ScreenshotAnchor,
  ScreenshotMimeType,
  SoftDeleteScreenshotAssetResponse,
} from "@/features/screenshots/api";
import type { ScreenshotFeedback } from "@/features/screenshots/extraction";

const SCREENSHOT_UPLOAD_MIME_TYPES: ScreenshotMimeType[] = ["image/png", "image/jpeg", "image/webp"];

export function normalizeScreenshotUploadMimeType(mimeType: string): ScreenshotMimeType | null {
  return SCREENSHOT_UPLOAD_MIME_TYPES.find((candidate) => candidate === mimeType) ?? null;
}

export function describeAssetLifecycleError(
  error: unknown,
  action: "annotate" | "delete" | "replace" | "upload",
): ScreenshotFeedback {
  return describeCommonApiError(error, {
    actionLabel:
      action === "annotate"
        ? "Annotation request"
        : action === "replace"
          ? "Replacement request"
          : action === "delete"
            ? "Delete request"
            : "Upload and attach",
    fallbackDescription:
      action === "annotate"
        ? "Screenshot annotation could not be applied."
        : action === "replace"
          ? "Screenshot replacement could not be requested."
          : action === "delete"
            ? "Screenshot asset could not be deleted."
            : "Screenshot asset could not be uploaded and attached.",
    failedTitle:
      action === "annotate"
        ? "Annotation request failed"
        : action === "replace"
          ? "Replacement request failed"
          : action === "delete"
            ? "Delete request failed"
            : "Upload and attach failed",
    invalidRequestTitle:
      action === "annotate"
        ? "Annotation request rejected"
        : action === "replace"
          ? "Replacement request rejected"
          : action === "delete"
            ? "Delete request rejected"
            : "Upload and attach rejected",
    noLeakDescription:
      "The screenshot asset context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
    noLeakTitle: "Screenshot asset context unavailable",
    rejectedTitle:
      action === "annotate"
        ? "Annotation request rejected"
        : action === "replace"
          ? "Replacement request rejected"
          : action === "delete"
            ? "Delete request rejected"
            : "Upload and attach rejected",
  });
}

export function describeAnnotatedScreenshot(
  response: AnnotateScreenshotResponse,
  previousActiveAssetId: string | null,
): ScreenshotFeedback {
  if (response.active_asset_id === previousActiveAssetId) {
    return {
      description: `Matching normalized annotation operations already resolve to rendered asset ${response.rendered_asset_id}. The current active view stays unchanged.`,
      title: "Existing annotated asset reused",
      tone: "success",
    };
  }

  return {
    description: `Annotation rendering completed. Anchor ${response.anchor_id} now resolves from base asset ${response.base_asset_id} to rendered asset ${response.rendered_asset_id}.`,
    title: "Annotated asset rendered",
    tone: "success",
  };
}

export function describeSoftDeletedAsset(
  response: SoftDeleteScreenshotAssetResponse,
): ScreenshotFeedback {
  return {
    description: response.active_asset_id
      ? `Asset ${response.deleted_asset_id} was deleted. Anchor ${response.anchor_id} now resolves to active asset ${response.active_asset_id}.`
      : `Asset ${response.deleted_asset_id} was deleted. Anchor ${response.anchor_id} no longer has an active asset.`,
    title: "Asset deleted",
    tone: "success",
  };
}

export function describeAttachedUpload(anchor: ScreenshotAnchor): ScreenshotFeedback {
  return {
    description: anchor.active_asset_id
      ? `Uploaded asset is now attached to anchor ${anchor.id}. Active asset ${anchor.active_asset_id} is linked to source version ${anchor.instruction_version_id}.`
      : `Uploaded asset attachment completed for anchor ${anchor.id}.`,
    title: "Uploaded asset attached",
    tone: "success",
  };
}

export async function computeBlobSha256(blob: Blob): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error("Browser crypto is unavailable for checksum generation.");
  }

  const buffer = await blob.arrayBuffer();
  const digest = await globalThis.crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function readImageDimensions(file: File): Promise<{ height: number; width: number }> {
  if (typeof Image === "undefined") {
    throw new Error("Image metadata APIs are unavailable in this environment.");
  }

  const objectUrl = URL.createObjectURL(file);

  try {
    return await new Promise<{ height: number; width: number }>((resolve, reject) => {
      const image = new Image();

      image.onload = () => {
        const width = image.naturalWidth || image.width;
        const height = image.naturalHeight || image.height;
        if (width > 0 && height > 0) {
          resolve({ height, width });
          return;
        }

        reject(new Error("Image dimensions could not be read."));
      };

      image.onerror = () => {
        reject(new Error("Image dimensions could not be read."));
      };

      image.src = objectUrl;
    });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export async function uploadFileToSignedUrl(
  uploadUrl: string,
  file: File,
  mimeType: ScreenshotMimeType,
): Promise<void> {
  const response = await fetch(uploadUrl, {
    body: file,
    headers: {
      "Content-Type": mimeType,
    },
    method: "PUT",
  });

  if (!response.ok) {
    throw new Error(`Signed upload failed with status ${response.status}.`);
  }
}
