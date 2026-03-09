import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LandRight | AI-Assisted Right-of-Way",
  description: "Attorney-in-the-loop automation for land agents, owners, and counsel.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
