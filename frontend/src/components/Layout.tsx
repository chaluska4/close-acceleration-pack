import { NavLink, Outlet } from "react-router-dom";
import { getMeta } from "../lib/adapter";
import { ErrorBoundary } from "./ErrorBoundary";

const NAV_ITEMS = [
  { to: "/", label: "Executive Overview", end: true },
  { to: "/variance", label: "Variance Analysis", end: false },
  { to: "/close", label: "Close Checklist & Controls", end: false },
  { to: "/outputs", label: "Outputs", end: false },
];

function navLinkClass(isActive: boolean): string {
  const base = "rounded-md px-3 py-2 text-sm font-medium transition-colors whitespace-nowrap";
  return isActive
    ? `${base} bg-[var(--color-navy)] text-white`
    : `${base} text-[var(--color-ink-secondary)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-navy)]`;
}

export function Layout() {
  const meta = getMeta();

  return (
    <div className="min-h-screen bg-[var(--color-surface-muted)]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-white focus:px-4 focus:py-2 focus:shadow-lg"
      >
        Skip to content
      </a>

      <header className="border-b border-[var(--color-border)] bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-5 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-accent)]">
                Automated FP&amp;A Month-End Close Workflow
              </p>
              <h1 className="text-2xl font-bold text-[var(--color-navy)]">{meta.product_name}</h1>
              <p className="mt-1 text-sm text-[var(--color-ink-secondary)]">
                {meta.company_name} &middot; Reporting Period: {meta.current_period_label}
              </p>
            </div>
            <a
              href={meta.github_url}
              target="_blank"
              rel="noreferrer"
              className="shrink-0 rounded-md border border-[var(--color-border)] px-3 py-2 text-xs font-medium text-[var(--color-ink-secondary)] transition-colors hover:border-[var(--color-navy)] hover:text-[var(--color-navy)]"
            >
              View technical implementation on GitHub
              <span aria-hidden="true"> ↗</span>
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          </div>

          <div
            role="note"
            aria-label="Synthetic data disclosure"
            className="rounded-md border border-[var(--color-accent)]/25 bg-[var(--color-accent-light)] px-3 py-2 text-xs text-[var(--color-navy)]"
          >
            <strong className="font-semibold">Portfolio project:</strong> {meta.data_disclosure}
          </div>

          <nav aria-label="Primary" className="-mx-1 flex gap-1 overflow-x-auto pb-1">
            {NAV_ITEMS.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => navLinkClass(isActive)}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>

      <footer className="mx-auto max-w-6xl px-4 py-8 text-center text-xs text-[var(--color-ink-muted)] sm:px-6">
        {meta.company_name_full} — synthetic portfolio project. Not real company reporting.
      </footer>
    </div>
  );
}
