import React, { type HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "strong" | "muted";
}

export function Panel({ className, variant = "default", ...props }: PanelProps) {
  const variantClass =
    variant === "strong"
      ? "surface-panel-strong"
      : variant === "muted"
        ? "surface-panel-muted"
        : "surface-panel";

  return (
    <div
      className={cn("rounded-[var(--radius-panel)] p-5 lg:p-6", variantClass, className)}
      {...props}
    />
  );
}

export function PanelHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mb-5 flex flex-col gap-2", className)} {...props} />;
}

export function PanelTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn("display-title text-[1.55rem] font-semibold text-[var(--text-primary)]", className)}
      {...props}
    />
  );
}

export function PanelDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm leading-6 text-[var(--text-muted)]", className)} {...props} />;
}
