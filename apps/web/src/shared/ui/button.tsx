import React, { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "default" | "compact";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--brand-primary)] text-[var(--text-inverse)] hover:bg-[var(--brand-primary-strong)]",
  secondary:
    "bg-transparent text-[var(--text-primary)] ring-1 ring-inset ring-[var(--line-strong)] hover:bg-[var(--brand-soft)]",
  ghost:
    "bg-transparent text-[var(--text-secondary)] hover:bg-[rgba(84,70,49,0.08)]",
};

const sizeClasses: Record<ButtonSize, string> = {
  default: "min-h-11 px-4 py-2.5 text-sm",
  compact: "min-h-9 px-3 py-2 text-sm",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, size = "default", type = "button", variant = "primary", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "focus-ring inline-flex items-center justify-center gap-2 rounded-[var(--radius-pill)] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55",
        sizeClasses[size],
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  );
});
