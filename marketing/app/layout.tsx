import type { Metadata } from "next";
import "./globals.css";
import { SiteFooter } from "./components/SiteFooter";
import { ThemeToggle } from "./components/ThemeToggle";

export const metadata: Metadata = {
  title: "LandGrantIQ | Operating system for Right-of-Way",
  description:
    "AI-assisted workflows for easements, ROW, and eminent domain—project execution, deadlines, and counsel-ready documentation in one place.",
};

const themeInitScript = `
(function(){
  try {
    var k = 'landgrant-marketing-theme';
    var t = localStorage.getItem(k);
    if (t === 'dark') document.documentElement.classList.add('dark');
    else if (t === 'light') document.documentElement.classList.remove('dark');
    else if (window.matchMedia('(prefers-color-scheme: dark)').matches) document.documentElement.classList.add('dark');
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="flex min-h-screen flex-col">
        <div className="flex shrink-0 items-center justify-end border-b border-slate-200/90 bg-slate-50/90 px-4 py-3 dark:border-white/10 dark:bg-slate-950/90">
          <ThemeToggle />
        </div>
        <main id="main-content" className="flex flex-1 flex-col">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
