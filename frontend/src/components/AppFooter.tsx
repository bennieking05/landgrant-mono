const VERSION = import.meta.env.VITE_APP_VERSION ?? "dev";
const BUILD_SHA = import.meta.env.VITE_BUILD_SHA ?? "local";

/** Slim trust footer (UX-2 / 1.7): legal + support links, version + build. */
export function AppFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white px-6 py-3 text-caption text-slate-500">
      <div className="flex flex-col items-center justify-between gap-2 sm:flex-row">
        <p>&copy; {new Date().getFullYear()} LandGrantIQ. All rights reserved.</p>
        <nav className="flex flex-wrap items-center gap-x-4 gap-y-1" aria-label="Legal and support">
          <a href="/terms" className="hover:text-slate-700">Terms</a>
          <a href="/privacy" className="hover:text-slate-700">Privacy</a>
          <a href="/security" className="hover:text-slate-700">Security</a>
          <a href="mailto:support@landgrantiq.com" className="hover:text-slate-700">Support</a>
          <span className="font-id text-slate-400" title="Application version and build">
            v{VERSION} &middot; {BUILD_SHA}
          </span>
        </nav>
      </div>
    </footer>
  );
}
