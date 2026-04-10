import Link from "next/link";

const year = new Date().getFullYear();

export function SiteFooter() {
  return (
    <footer className="border-t border-slate-200/90 bg-slate-50/80 py-8 text-sm text-slate-600 dark:border-white/10 dark:bg-slate-950/80 dark:text-slate-400">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-6 sm:flex-row sm:gap-6">
        <p className="order-2 text-center sm:order-1 sm:text-left">
          © {year} LandGrant. All rights reserved.
        </p>
        <nav className="order-1 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 sm:order-2" aria-label="Legal">
          <Link href="/privacy" className="text-slate-700 underline-offset-4 transition hover:text-brand dark:text-slate-300 dark:hover:text-white">
            Privacy Policy
          </Link>
          <Link href="/terms" className="text-slate-700 underline-offset-4 transition hover:text-brand dark:text-slate-300 dark:hover:text-white">
            Terms of Use
          </Link>
          <a
            href="mailto:hello@landgrant.ai"
            className="text-slate-700 underline-offset-4 transition hover:text-brand dark:text-slate-300 dark:hover:text-white"
          >
            Contact
          </a>
        </nav>
      </div>
    </footer>
  );
}
