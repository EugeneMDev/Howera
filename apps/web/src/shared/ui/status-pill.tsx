import React, { type HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

type StatusTone = "info" | "success" | "warning" | "danger" | "neutral";

const toneClasses: Record<StatusTone, string> = {
  info: "bg-[var(--status-info-soft)] text-[var(--status-info)]",
  success: "bg-[var(--status-success-soft)] text-[var(--status-success)]",
  warning: "bg-[var(--status-warning-soft)] text-[var(--status-warning)]",
  danger: "bg-[var(--status-danger-soft)] text-[var(--status-danger)]",
  neutral: "bg-[rgba(84,70,49,0.10)] text-[var(--text-secondary)]",
};

interface StatusPillProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: StatusTone;
}

export function StatusPill({ className, tone = "neutral", ...props }: StatusPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-[var(--radius-pill)] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em]",
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
