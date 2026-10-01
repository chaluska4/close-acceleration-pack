import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/** Catches render-time errors in any tab (e.g. a malformed/missing field
 * in the exported data) so one broken panel shows a clear message instead
 * of a blank white screen for the whole app. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Close Acceleration Pack — render error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div
          role="alert"
          className="mx-auto my-12 max-w-lg rounded-xl border border-[var(--color-critical)]/30 bg-[var(--color-critical-bg)] p-6 text-center"
        >
          <p className="font-semibold text-[var(--color-critical)]">Something went wrong loading this view.</p>
          <p className="mt-2 text-sm text-[var(--color-ink-secondary)]">
            {this.state.error.message || "An unexpected error occurred."}
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
