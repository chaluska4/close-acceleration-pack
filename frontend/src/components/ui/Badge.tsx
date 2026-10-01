import type { ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  className?: string;
  dotClassName?: string;
  showDot?: boolean;
}

/** A small status pill with an optional leading color dot. Used for RAG,
 * task status, and control status everywhere in the app — one visual
 * language for "status" across all three tabs. */
export function Badge({ children, className = "", dotClassName, showDot = true }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${className}`}
    >
      {showDot && dotClassName ? (
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotClassName}`} aria-hidden="true" />
      ) : null}
      {children}
    </span>
  );
}
