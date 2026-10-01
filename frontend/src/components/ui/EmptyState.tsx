interface EmptyStateProps {
  message: string;
}

/** Shown in place of a list/table when the underlying data genuinely has
 * nothing to display (e.g. zero exception tasks this period) — an
 * intentional, labeled state rather than blank space. */
export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="px-5 py-8 text-center text-sm text-[var(--color-ink-muted)]">{message}</div>
  );
}
