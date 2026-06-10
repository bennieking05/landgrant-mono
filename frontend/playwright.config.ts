import { defineConfig, devices } from "@playwright/test";
import path from "path";

/**
 * LandGrant Playwright Configuration
 *
 * Run tests:
 *   npm run test:e2e          # headless regression
 *   npm run test:e2e:headed   # visible browser
 *   npm run test:e2e:debug    # step-through debugger
 *   npm run test:evidence     # capture evidence screenshots
 *   npm run test:regression   # full regression + evidence
 */

const ARTIFACTS_DIR = path.resolve(__dirname, "..", "artifacts", "e2e");

export default defineConfig({
  testDir: "./tests",
  testMatch: ["**/e2e/**/*.spec.ts", "**/evidence/**/*.spec.ts"],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["html", { outputFolder: path.join(ARTIFACTS_DIR, "report") }],
    ["list"],
    ["json", { outputFile: path.join(ARTIFACTS_DIR, "test-results.json") }],
  ],
  use: {
    baseURL: process.env.VITE_API_BASE
      ? process.env.VITE_API_BASE.replace(":8050", ":3050")
      : "http://localhost:3050",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  outputDir: path.join(ARTIFACTS_DIR, "test-results"),
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 5"] },
    },
  ],
  /* Boot the backend (8050) and frontend (3050) before tests. A reachable
   * Postgres (see docker-compose) is still required for backend auth. */
  webServer: [
    {
      command: "python3 -m uvicorn app.main:app --port 8050",
      cwd: path.resolve(__dirname, "..", "backend"),
      url: "http://localhost:8050/health/live",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:3050",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
