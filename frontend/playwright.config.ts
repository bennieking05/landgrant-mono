import { defineConfig, devices } from "@playwright/test";
import path from "path";

/**
 * LandGrant Playwright Configuration
 *
 * Run tests:
 *   npm run test:e2e          # headless regression
 *   npm run test:e2e:headed   # visible browser
 *   npm run test:evidence     # capture evidence screenshots
 *   npm run test:gallery      # empty-state screenshots (optional CLEAR_GALLERY_DB=1)
 *
 * Remote / staging: PLAYWRIGHT_REMOTE=1, E2E_STAGING_BASE_URL, VITE_API_BASE
 */

const ARTIFACTS_DIR = path.resolve(__dirname, "..", "artifacts", "e2e");
const remote = process.env.PLAYWRIGHT_REMOTE === "1";

const baseURL =
  process.env.E2E_STAGING_BASE_URL ||
  process.env.PLAYWRIGHT_BASE_URL ||
  (process.env.VITE_API_BASE
    ? process.env.VITE_API_BASE.replace(":8050", ":3050")
    : "http://localhost:3050");

export default defineConfig({
  testDir: "./tests",
  testMatch: ["**/e2e/**/*.spec.ts", "**/evidence/**/*.spec.ts"],
  globalSetup: remote ? undefined : "./tests/e2e/global-setup.ts",
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
    baseURL,
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
      testIgnore: /empty-db-gallery\.spec\.ts|a11y-.*\.spec\.ts|staging-smoke\.spec\.ts/,
      use: { ...devices["Pixel 5"] },
    },
  ],
  ...(remote
    ? {}
    : {
        webServer: [
          {
            command: "python3 -m uvicorn app.main:app --port 8050",
            cwd: path.resolve(__dirname, "..", "backend"),
            url: "http://localhost:8050/health/live",
            reuseExistingServer: !process.env.CI,
            timeout: 120_000,
            env: { ...process.env },
          },
          {
            command: "npm run dev",
            url: "http://localhost:3050",
            reuseExistingServer: !process.env.CI,
            timeout: 120_000,
            env: { ...process.env },
          },
        ],
      }),
});
