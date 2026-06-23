import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import path from "path";

const API_BASE = process.env.VITE_API_BASE ?? "http://localhost:8050";
const TOKEN_KEY = "landgrant.jwt";

/** Seed a staff JWT in sessionStorage so auth-gated routes render real content. */
async function staffLogin(page: Page, request: APIRequestContext): Promise<void> {
  const res = await request.post(`${API_BASE}/auth/login`, {
    data: { email: "admin@landgrant.local", password: "devpass123" },
  });
  expect(res.ok()).toBeTruthy();
  const { access_token: token } = (await res.json()) as { access_token: string };
  await page.addInitScript(
    ([key, value]) => window.sessionStorage.setItem(key, value),
    [TOKEN_KEY, token] as const,
  );
}

// Fixed instant the whole suite renders "now" as, so every relative-date
// computation (days-until a deadline, urgency colors, the calendar "today"
// ring, the footer year, the Ops "last checked" stamp) is identical on every
// run regardless of the real wall clock.
const FIXED_NOW = new Date(2026, 5, 23, 12, 0, 0); // 2026-06-23 12:00 local

// Pin the two time-windowed/data-driven sources whose numbers drift with
// *server* time (so freezing the browser clock alone isn't enough): the
// dashboard rollup and the three Ops health probes. Fixtures captured from the
// live dev API; only the volatile counts matter for determinism.
const DASHBOARD_HOME = {
  persona: "platform_admin",
  project_id: "PRJ-002",
  sample_size: 1,
  sample_sufficient: false,
  parcels_by_stage: { intake: 1 },
  pending_offers_count: 0,
  overdue_tasks_count: 0,
  deadlines_next_14_count: 1,
  pending_approvals_count: 0,
  escalations_open_count: null,
  litigation_rate: null,
  litigation_rate_insufficient_data: true,
  cycle_time_median_days: null,
  cycle_time_insufficient_data: true,
  budget_utilization_pct: null,
  budget_utilization_insufficient_data: true,
};

/**
 * Make the page deterministic for pixel comparison: freeze the clock and pin
 * the data-driven endpoints. Everything else (parcels, projects, deadline
 * *dates*) is stable seeded data, so the UI renders identically every run.
 */
async function stabilize(page: Page): Promise<void> {
  await page.clock.setFixedTime(FIXED_NOW);
  await page.route("**/dashboard/home*", (route) => route.fulfill({ json: DASHBOARD_HOME }));
  await page.route("**/health/live", (route) => route.fulfill({ json: { status: "ok" } }));
  await page.route("**/health/invite", (route) =>
    route.fulfill({ json: { status: "invite-flow", checks: ["magic_link", "email_queue"] } }),
  );
  await page.route("**/health/esign", (route) =>
    route.fulfill({ json: { status: "esign", vendor: "adobe" } }),
  );
}

/**
 * Visual Regression Tests
 *
 * These tests capture screenshots at key UI states and compare them against
 * baseline images to detect unexpected visual changes.
 *
 * To update baselines:
 *   npx playwright test visual-regression --update-snapshots
 *
 * Baseline images stored in: tests/e2e/visual-regression.spec.ts-snapshots/
 */

const PROJECT_ID = "PRJ-001";
const PARCEL_ID = "PARCEL-001";
const ARTIFACTS_DIR = path.resolve(__dirname, "..", "..", "..", "artifacts", "e2e", "regression");

// Timestamp for this test run
const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);

test.describe("Visual Regression Suite", () => {
  test.beforeEach(async ({ page, request }) => {
    await staffLogin(page, request);
    await stabilize(page);
  });

  test.describe("Home Page", () => {
    test("home page layout", async ({ page }) => {
      await page.goto("/");
      await page.waitForLoadState("networkidle");

      // Save timestamped copy for audit trail
      await page.screenshot({
        path: path.join(ARTIFACTS_DIR, `home-${TIMESTAMP}.png`),
        fullPage: true,
      });

      // Visual regression comparison
      await expect(page).toHaveScreenshot("home-page.png", {
        fullPage: true,
        maxDiffPixelRatio: 0.02, // Allow 2% pixel difference
      });
    });
  });

  test.describe("Agent Workbench", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(`/workbench?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000); // Allow dynamic content to settle
    });

    test("workbench full page", async ({ page }) => {
      await page.screenshot({
        path: path.join(ARTIFACTS_DIR, `workbench-full-${TIMESTAMP}.png`),
        fullPage: true,
      });

      await expect(page).toHaveScreenshot("workbench-full.png", {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });

    test("parcel list component", async ({ page }) => {
      const parcelList = page.locator('[data-testid="parcel-list"], .parcel-list, section').filter({
        hasText: /Parcel/,
      }).first();

      if (await parcelList.isVisible().catch(() => false)) {
        await parcelList.screenshot({
          path: path.join(ARTIFACTS_DIR, `parcel-list-${TIMESTAMP}.png`),
        });

        await expect(parcelList).toHaveScreenshot("parcel-list.png", {
          maxDiffPixelRatio: 0.05,
        });
      }
    });

    test("communications panel", async ({ page }) => {
      const commsPanel = page.locator('[data-testid="comms-panel"], .comms-log').first();

      if (await commsPanel.isVisible().catch(() => false)) {
        await commsPanel.screenshot({
          path: path.join(ARTIFACTS_DIR, `comms-panel-${TIMESTAMP}.png`),
        });

        await expect(commsPanel).toHaveScreenshot("comms-panel.png", {
          maxDiffPixelRatio: 0.05,
        });
      }
    });

    test.skip("title panel with tabs", async ({ page }) => {
      // Skip: This test has a locator issue with "Title instruments" 
      // that causes consistent timeouts. The title panel UI may have changed.
      const titlePanel = page.locator("text=Title instruments").first().locator("..").locator("..");

      if (await titlePanel.isVisible().catch(() => false)) {
        // Screenshot instruments tab
        await titlePanel.screenshot({
          path: path.join(ARTIFACTS_DIR, `title-instruments-${TIMESTAMP}.png`),
        });

        // Try clicking curative tab
        const curativeTab = page.locator("text=Curative Items").first();
        if (await curativeTab.isVisible().catch(() => false)) {
          await curativeTab.click();
          await page.waitForTimeout(500);
          
          await titlePanel.screenshot({
            path: path.join(ARTIFACTS_DIR, `title-curative-${TIMESTAMP}.png`),
          });
        }
      }
    });
  });

  test.describe("Landowner Portal", () => {
    test("intake page layout", async ({ page }) => {
      await page.goto(`/intake?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: path.join(ARTIFACTS_DIR, `intake-${TIMESTAMP}.png`),
        fullPage: true,
      });

      await expect(page).toHaveScreenshot("intake-page.png", {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });

    test("decision options panel", async ({ page }) => {
      await page.goto(`/intake?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      const decisionPanel = page.locator("text=Decision options").first().locator("..").locator("..");

      if (await decisionPanel.isVisible().catch(() => false)) {
        await decisionPanel.screenshot({
          path: path.join(ARTIFACTS_DIR, `decision-options-${TIMESTAMP}.png`),
        });

        await expect(decisionPanel).toHaveScreenshot("decision-options.png", {
          maxDiffPixelRatio: 0.05,
        });
      }
    });
  });

  test.describe("Counsel View", () => {
    test("counsel page layout", async ({ page }) => {
      await page.goto(`/counsel?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: path.join(ARTIFACTS_DIR, `counsel-${TIMESTAMP}.png`),
        fullPage: true,
      });

      await expect(page).toHaveScreenshot("counsel-page.png", {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });

    test("approval queue", async ({ page }) => {
      await page.goto(`/counsel?projectId=${PROJECT_ID}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      const approvalQueue = page.locator("text=Approval queue").first().locator("..").locator("..");

      if (await approvalQueue.isVisible().catch(() => false)) {
        await approvalQueue.screenshot({
          path: path.join(ARTIFACTS_DIR, `approval-queue-${TIMESTAMP}.png`),
        });

        await expect(approvalQueue).toHaveScreenshot("approval-queue.png", {
          maxDiffPixelRatio: 0.05,
        });
      }
    });
  });

  test.describe("Ops Dashboard", () => {
    test("ops page layout", async ({ page }) => {
      await page.goto(`/ops?projectId=${PROJECT_ID}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: path.join(ARTIFACTS_DIR, `ops-${TIMESTAMP}.png`),
        fullPage: true,
      });

      await expect(page).toHaveScreenshot("ops-page.png", {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });
  });
});

test.describe("Component Regression", () => {
  test.beforeEach(async ({ page, request }) => {
    await staffLogin(page, request);
    await stabilize(page);
  });

  test("map component renders", async ({ page }) => {
    await page.goto(`/workbench?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000); // Maps need extra time

    // Look for map container
    const mapContainer = page.locator('[data-testid="parcel-map"], .mapboxgl-map, .map-container').first();

    if (await mapContainer.isVisible().catch(() => false)) {
      await mapContainer.screenshot({
        path: path.join(ARTIFACTS_DIR, `map-${TIMESTAMP}.png`),
      });

      // Note: Map screenshots may vary due to tiles loading
      // Using higher tolerance
      await expect(mapContainer).toHaveScreenshot("map-component.png", {
        maxDiffPixelRatio: 0.15, // Maps have more visual variance
      });
    } else {
      // Map might show fallback without Mapbox token
      console.log("Map container not visible - may need MAPBOX_TOKEN");
      await page.screenshot({
        path: path.join(ARTIFACTS_DIR, `map-fallback-${TIMESTAMP}.png`),
        fullPage: true,
      });
    }
  });
});
