import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Vitest config kept separate from ``vite.config.ts`` so the ``test``
// property doesn't show up as unknown in ``tsc --noEmit`` against the
// public Vite types.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    // Keep Playwright tests (under ``tests/``) out of Vitest; Playwright
    // ships its own runner and setup.
    exclude: ["node_modules", "dist", "tests/**"],
    coverage: {
      reporter: ["text", "html"],
      exclude: ["node_modules", "dist", "tests/**", "src/**/*.d.ts"],
    },
  },
});
