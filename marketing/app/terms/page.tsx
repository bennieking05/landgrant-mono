import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Use | LandGrant",
  description: "LandGrant marketing site terms of use.",
};

export default function TermsPage() {
  return (
    <article className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-6 py-12 text-slate-800 dark:text-slate-200">
      <p className="text-sm text-slate-500 dark:text-slate-400">
        <Link href="/" className="text-brand hover:underline">
          Home
        </Link>
      </p>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Terms of Use</h1>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Last updated: April 9, 2026</p>

      <div className="mt-8 max-w-none space-y-6 text-slate-700 leading-relaxed dark:text-slate-300">
        <p>
          These terms govern your use of the LandGrant marketing website. They are provided as a placeholder for
          review by your legal team; they are not a substitute for jurisdiction-specific advice.
        </p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Acceptance</h2>
        <p>By accessing this site, you agree to these terms. If you do not agree, do not use the site.</p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">No professional advice</h2>
        <p>
          Content on this site is for general information only. It does not create an attorney–client relationship
          and is not legal, financial, or engineering advice for any specific matter.
        </p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Intellectual property</h2>
        <p>
          LandGrant names, logos, and site content are protected by applicable intellectual property laws. Do not
          copy or redistribute materials without permission, except as allowed by law.
        </p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Disclaimer of warranties</h2>
        <p>
          This site is provided “as is.” To the fullest extent permitted by law, we disclaim warranties of
          merchantability, fitness for a particular purpose, and non-infringement.
        </p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Limitation of liability</h2>
        <p>
          To the fullest extent permitted by law, LandGrant and its affiliates will not be liable for indirect,
          incidental, or consequential damages arising from your use of this site.
        </p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Changes</h2>
        <p>We may update these terms. Continued use after changes constitutes acceptance of the revised terms.</p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Contact</h2>
        <p>
          Questions:{" "}
          <a href="mailto:hello@landgrant.ai" className="text-brand underline-offset-2 hover:underline">
            hello@landgrant.ai
          </a>
          .
        </p>
      </div>
    </article>
  );
}
