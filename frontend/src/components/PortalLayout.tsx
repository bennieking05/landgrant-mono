import { useTranslation } from "react-i18next";
import { LifeBuoy, Scale } from "lucide-react";
import { Logo, Select } from "@/components/ui";
import { setStoredLocale } from "@/i18n";

/**
 * Landowner portal chrome (UX-8): a second design language on the same tokens -
 * large type, single column, calm and reassuring, mobile-first. Deliberately
 * NOT the enterprise sidebar. No notification polling here (also avoids the
 * mobile never-network-idle loop).
 */
export function PortalLayout({ children }: { children: React.ReactNode }) {
  const { t, i18n } = useTranslation();

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[120] focus:rounded-control focus:bg-brand focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-2xl items-center justify-between px-4 py-4">
          <Logo size={28} />
          <label className="flex items-center gap-2">
            <span className="sr-only">{t("app.language")}</span>
            <Select
              value={i18n.language.startsWith("es") ? "es" : "en"}
              onChange={(e) => {
                void i18n.changeLanguage(e.target.value);
                setStoredLocale(e.target.value);
              }}
              className="h-9 w-28"
              aria-label={t("app.language")}
            >
              <option value="en">{t("app.english")}</option>
              <option value="es">{t("app.spanish")}</option>
            </Select>
          </label>
        </div>
      </header>

      <main id="main-content" className="mx-auto w-full max-w-2xl flex-1 px-4 py-8">
        {children}
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto w-full max-w-2xl space-y-4 px-4 py-6">
          <div className="rounded-card border border-info-border bg-info-bg p-4">
            <p className="flex items-center gap-2 text-h3 text-info-fg">
              <LifeBuoy className="h-5 w-5" /> {t("portal.help")}
            </p>
            <p className="mt-1 text-body text-slate-700">{t("portal.helpBody")}</p>
          </div>
          <div className="flex items-start gap-2 text-small text-slate-600">
            <Scale className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
            <p>{t("portal.disclaimer")}</p>
          </div>
          <nav className="flex flex-wrap gap-x-4 gap-y-1 text-caption text-slate-500" aria-label="Legal">
            <a href="/terms" className="hover:text-slate-700">Terms</a>
            <a href="/privacy" className="hover:text-slate-700">Privacy</a>
            <a href="/security" className="hover:text-slate-700">Security</a>
            <a href="mailto:help@landgrantiq.com" className="hover:text-slate-700">Support</a>
            <span className="text-slate-400">&copy; {new Date().getFullYear()} LandGrantIQ</span>
          </nav>
        </div>
      </footer>
    </div>
  );
}
