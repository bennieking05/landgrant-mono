import type { Config } from "tailwindcss";

/**
 * LandGrantIQ design tokens (UX-1).
 * "Institutional, precise, calm" - closer to a financial terminal than a consumer app.
 * Do not introduce raw hex in components; consume these tokens.
 */
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "IBM Plex Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      fontSize: {
        // name: [size, lineHeight] - the disciplined scale from UX-1
        display: ["1.875rem", { lineHeight: "2.25rem", fontWeight: "600" }], // 30/36
        h1: ["1.5rem", { lineHeight: "2rem", fontWeight: "600" }], // 24/32
        h2: ["1.125rem", { lineHeight: "1.75rem", fontWeight: "600" }], // 18/28
        h3: ["1rem", { lineHeight: "1.5rem", fontWeight: "600" }], // 16/24
        body: ["0.875rem", { lineHeight: "1.25rem" }], // 14/20
        small: ["0.8125rem", { lineHeight: "1.125rem" }], // 13/18
        caption: ["0.75rem", { lineHeight: "1rem", letterSpacing: "0.04em" }], // 12/16
      },
      colors: {
        // Primary navy family, generated from #1F4B99 (brand-600).
        navy: {
          50: "#EFF4FB",
          100: "#DBE6F5",
          200: "#BCD0EC",
          300: "#8FB0DD",
          400: "#5B86C7",
          500: "#3A66B0",
          600: "#1F4B99",
          700: "#1A3E7E",
          800: "#16315F",
          900: "#14294A",
          950: "#0F1B30",
        },
        // Back-compat brand alias (existing components use bg-brand / text-brand / hover:bg-brand-dark).
        brand: {
          DEFAULT: "#1F4B99",
          dark: "#16315F",
          fg: "#FFFFFF",
        },
        // Copper accent (the "IQ" + status accents).
        accent: {
          DEFAULT: "#B26A2C",
          50: "#FBF3EB",
          100: "#F3E0CC",
          300: "#E0AE73",
          400: "#D98B45",
          500: "#C2772F",
          600: "#B26A2C",
          700: "#8F5322",
        },
        // Semantic status, each meeting >=4.5:1 for fg on bg.
        success: { DEFAULT: "#15803D", bg: "#ECFDF3", border: "#ABEFC6", fg: "#0A5226" },
        warning: { DEFAULT: "#B45309", bg: "#FFF8EB", border: "#FEDF89", fg: "#7A3E06" },
        danger: { DEFAULT: "#B42318", bg: "#FEF3F2", border: "#FECDCA", fg: "#7A271A" },
        info: { DEFAULT: "#175CD3", bg: "#EFF6FF", border: "#B2D4FF", fg: "#0B3A8A" },
        // Parcel workflow stages: 8-hue categorical ramp, deuteranopia-checked, always paired with a text label.
        stage: {
          intake: { bg: "#EEF2F6", fg: "#334155", border: "#CBD5E1" },
          appraisal: { bg: "#EAF4FF", fg: "#0B4FA8", border: "#B2D4FF" },
          offerPending: { bg: "#FFF6E8", fg: "#92590B", border: "#F6D88A" },
          offerSent: { bg: "#FDF2E3", fg: "#8F5322", border: "#E8C79A" },
          negotiation: { bg: "#F3EEFC", fg: "#5B2A91", border: "#D9C6F2" },
          closing: { bg: "#E9F7F1", fg: "#0A6B4A", border: "#A7E0CC" },
          litigation: { bg: "#FDECEC", fg: "#A41B14", border: "#F4B9B5" },
          closed: { bg: "#F1F3F5", fg: "#5B6776", border: "#D3DAE2" },
        },
        // Risk bands (paired with numeric score + label, never color alone).
        risk: {
          low: { bg: "#ECFDF3", fg: "#0A5226", border: "#ABEFC6" },
          medium: { bg: "#FFF8EB", fg: "#7A3E06", border: "#FEDF89" },
          high: { bg: "#FEF3F2", fg: "#7A271A", border: "#FECDCA" },
        },
      },
      borderRadius: {
        control: "6px",
        card: "12px",
        modal: "16px",
      },
      boxShadow: {
        // Two elevation levels only (UX-1).
        card: "0 1px 2px 0 rgb(16 27 48 / 0.06), 0 1px 3px 0 rgb(16 27 48 / 0.08)",
        overlay: "0 12px 32px -8px rgb(16 27 48 / 0.24), 0 4px 12px -4px rgb(16 27 48 / 0.12)",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      transitionDuration: {
        fast: "150ms",
        base: "200ms",
      },
    },
  },
  plugins: [],
};

export default config;
