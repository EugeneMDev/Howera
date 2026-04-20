import React, { forwardRef, type TextareaHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, rows = 12, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={cn(
        "focus-ring min-h-32 w-full rounded-[var(--radius-card)] border bg-white/80 px-4 py-3 text-sm leading-7 text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]",
        className,
      )}
      style={{ borderColor: "var(--line-strong)" }}
      {...props}
    />
  );
});
