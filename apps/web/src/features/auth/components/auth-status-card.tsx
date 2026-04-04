"use client";

import React from "react";

import { ErrorState, LoadingState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";

interface AuthStatusCardProps {
  actionLabel?: string;
  description: string;
  mode: "loading" | "redirecting" | "error";
  onAction?: () => void;
  title: string;
}

export function AuthStatusCard({
  actionLabel,
  description,
  mode,
  onAction,
  title,
}: AuthStatusCardProps) {
  if (mode === "error") {
    return (
      <ErrorState
        action={
          actionLabel && onAction ? (
            <Button size="compact" variant="secondary" onClick={onAction}>
              {actionLabel}
            </Button>
          ) : undefined
        }
        description={description}
        title={title}
      />
    );
  }

  return <LoadingState description={description} title={title} />;
}
