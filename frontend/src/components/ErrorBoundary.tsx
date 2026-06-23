import { Component, type ErrorInfo, type ReactNode } from "react";
import * as Sentry from "@sentry/react";

type Props = { children: ReactNode };
type State = { error: Error | null };

/**
 * App-level error boundary. A render error in any single component (e.g. a bad
 * data shape, a Radix Slot misuse) would otherwise unmount the entire React
 * tree and leave a blank white screen. This catches the error, reports it to
 * Sentry when configured, and shows a recoverable fallback so the rest of the
 * shell stays usable after a reload.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface in dev consoles and ship to Sentry in environments that have it.
    console.error("Unhandled UI error:", error, info.componentStack);
    if (import.meta.env.VITE_SENTRY_DSN) {
      Sentry.captureException(error, { extra: { componentStack: info.componentStack } });
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div
          role="alert"
          className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center text-slate-700"
        >
          <h1 className="text-h2 font-semibold text-slate-900">Something went wrong</h1>
          <p className="max-w-md text-small text-slate-600">
            An unexpected error occurred while rendering this page. Reloading usually fixes it. If
            the problem persists, please contact support.
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              className="rounded-control bg-brand px-4 py-2 text-small font-medium text-white hover:bg-brand-dark"
              onClick={() => window.location.reload()}
            >
              Reload
            </button>
            <a
              className="rounded-control border border-slate-300 px-4 py-2 text-small font-medium text-slate-700 hover:bg-slate-50"
              href="/"
            >
              Back to home
            </a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
