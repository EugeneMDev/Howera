import React, { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, type = "text", ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      type={type}
      className={cn(
        "focus-ring min-h-11 w-full rounded-[var(--radius-card)] border bg-white/80 px-3 py-2.5 text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]",
        className,
      )}
      style={{ borderColor: "var(--line-strong)" }}
      {...props}
    />
  );
});
