import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy | LandGrant",
  description: "LandGrant marketing site privacy policy.",
};

export default function PrivacyPage() {
  return (
    <article className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-6 py-12 text-slate-800 dark:text-slate-200">
      <p className="text-sm text-slate-500 dark:text-slate-400">
        <Link href="/" className="text-brand hover:underline">
          Home
        </Link>
      </p>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Privacy Policy</h1>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Last updated: April 9, 2026</p>

      <div className="mt-8 max-w-none space-y-6 text-slate-700 leading-relaxed dark:text-slate-300">
        <p>
          This page describes how the LandGrant marketing website (“we,” “us”) handles information when you browse
          pages on this site or contact us by email. It is a general summary for transparency. Your counsel should
          review any policy before you rely on it for compliance purposes.
        </p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Information we collect</h2>
        <p>
          If you send email to an address published on this site, we receive the contents of your message and your
          email address. Standard server logs may include IP address, browser type, and timestamps when you request
          pages.
        </p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">How we use information</h2>
        <p>
          We use contact information to respond to inquiries. We use log data for security and to improve site
          reliability. We do not sell personal information from this marketing site.
        </p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Cookies and storage</h2>
        <p>
          This site may store a preference (such as theme choice) in your browser&apos;s local storage to improve your
          experience. You can clear site data in your browser settings at any time.
        </p>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Changes</h2>
        <p>We may update this policy periodically. The “Last updated” date above will change when we do.</p>
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
