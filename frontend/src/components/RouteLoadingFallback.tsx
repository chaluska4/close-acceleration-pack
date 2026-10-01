/** Shown briefly while a tab's code chunk loads over the network (route-
 * level code splitting — see App.tsx). A real async state, not simulated. */
export function RouteLoadingFallback() {
  return (
    <div role="status" aria-live="polite" className="flex items-center justify-center py-24">
      <span className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}
