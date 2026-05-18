/**
 * Core Flows Evidence Screenshot Capture
 *
 * Captures responsive screenshots for each primary user journey. Routes here
 * MUST stay in sync with `frontend/src/App.tsx`; previously this file hit a
 * number of paths (e.g. `/cases`, `/parcels`, `/settlement`, `/tasks`,
 * `/templates`, `/ai-decisions`, `/predictions`) that do not exist and were
 * silently redirected, so the screenshots captured the wrong screen.
 *
 * The suite seeds the `admin` persona in `localStorage` before each test so
 * persona-gated pages (`/intake`, `/counsel`, `/ops`, `/admin`, `/firm-admin`)
 * render instead of redirecting to the dashboard.
 *
 * Run: npm run test:evidence
 *
 * Environment variables:
 *   FEATURE_NAME - Name of feature/branch (default: 'regression')
 *   EVIDENCE_TS  - Timestamp for folder (default: auto-generated)
 */

import { test, expect } from "@playwright/test";
import {
  captureResponsiveScreenshots,
  generateEvidenceSummary,
  printEvidenceSummary,
  VIEWPORTS,
} from "../utils/screenshot";

const collectedScreenshots: string[] = [];

test.describe("Evidence Screenshots - Core Flows", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    // Pre-set the admin persona so persona-gated routes are reachable. This
    // mirrors how the AppContextProvider hydrates `persona` on mount.
    await page.addInitScript(() => {
      try {
        window.localStorage.setItem("landgrant.persona", "admin");
      } catch {
        /* localStorage may be unavailable */
      }
    });
  });

  test.afterAll(async () => {
    const summary = generateEvidenceSummary(collectedScreenshots);
    printEvidenceSummary(summary, collectedScreenshots.length / 2);
  });

  test("01 - Dashboard (home)", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "01-dashboard");
    collectedScreenshots.push(desktop, mobile);
    await expect(page).toHaveTitle(/LandGrant/i);
  });

  test("02 - Admin projects / cases", async ({ page }) => {
    await page.goto("/admin");
    await page.waitForLoadState("networkidle");
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "02-admin-projects");
    collectedScreenshots.push(desktop, mobile);
  });

  test("03 - Landowner intake wizard", async ({ page }) => {
    await page.goto("/intake");
    await page.waitForLoadState("networkidle");
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "03-intake");
    collectedScreenshots.push(desktop, mobile);
  });

  test("04 - Agent workbench (parcels + pipeline)", async ({ page }) => {
    await page.goto("/workbench");
    await page.waitForLoadState("networkidle");
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "04-workbench");
    collectedScreenshots.push(desktop, mobile);
  });

  test("05 - Counsel approvals (templates + AI review)", async ({ page }) => {
    await page.goto("/counsel");
    await page.waitForLoadState("networkidle");
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "05-counsel-approvals");
    collectedScreenshots.push(desktop, mobile);
    // CounselPage now exposes the AI audit drawer trigger. Assert it's
    // mounted so the orphaned-UI regression we just fixed stays fixed.
    await expect(page.getByTestId("open-ai-audit")).toBeVisible();
  });

  test("06 - Counsel binder & deadlines", async ({ page }) => {
    await page.goto("/counsel");
    await page.waitForLoadState("networkidle");
    const binderTab = page.getByRole("tab", { name: /binder/i }).or(
      page.locator('button:has-text("Binder & deadlines")'),
    );
    if (await binderTab.first().isVisible().catch(() => false)) {
      await binderTab.first().click();
      await page.waitForLoadState("networkidle");
    }
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "06-counsel-binder");
    collectedScreenshots.push(desktop, mobile);
  });

  test("07 - Counsel AI Copilot", async ({ page }) => {
    await page.goto("/counsel");
    await page.waitForLoadState("networkidle");
    const copilotBtn = page
      .locator('[data-testid="copilot-toggle"], button:has-text("Copilot"), button:has-text("AI Copilot")')
      .first();
    if (await copilotBtn.isVisible().catch(() => false)) {
      await copilotBtn.click();
      await page.waitForTimeout(500);
    }
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "07-copilot-panel");
    collectedScreenshots.push(desktop, mobile);
  });

  test("08 - Counsel tasks", async ({ page }) => {
    await page.goto("/counsel");
    await page.waitForLoadState("networkidle");
    const tasksTab = page.getByRole("tab", { name: /^tasks$/i }).or(
      page.locator('button:has-text("Tasks")'),
    );
    if (await tasksTab.first().isVisible().catch(() => false)) {
      await tasksTab.first().click();
      await page.waitForLoadState("networkidle");
    }
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "08-counsel-tasks");
    collectedScreenshots.push(desktop, mobile);
  });

  test("09 - Counsel litigation", async ({ page }) => {
    await page.goto("/counsel");
    await page.waitForLoadState("networkidle");
    const tab = page.getByRole("tab", { name: /litigation/i }).or(
      page.locator('button:has-text("Litigation")'),
    );
    if (await tab.first().isVisible().catch(() => false)) {
      await tab.first().click();
      await page.waitForLoadState("networkidle");
    }
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "09-counsel-litigation");
    collectedScreenshots.push(desktop, mobile);
  });

  test("10 - Ops dashboard", async ({ page }) => {
    await page.goto("/ops");
    await page.waitForLoadState("networkidle");
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "10-ops");
    collectedScreenshots.push(desktop, mobile);
    // OpsPage now exposes a live integration panel wired to /health/*
    // endpoints. Assert the probes are mounted so a regression that removes
    // the panel fails the evidence run instead of producing a silent diff.
    await expect(page.getByTestId("integration-status")).toBeVisible();
    await expect(page.getByTestId("integration-api")).toBeVisible();
  });

  test("11 - Firm admin", async ({ page }) => {
    await page.goto("/firm-admin");
    await page.waitForLoadState("networkidle");
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "11-firm-admin");
    collectedScreenshots.push(desktop, mobile);
  });

  test("12 - Notifications", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const notifBell = page
      .locator('[data-testid="notification-bell"], button[aria-label*="notification"]')
      .first();
    if (await notifBell.isVisible().catch(() => false)) {
      await notifBell.click();
      await page.waitForTimeout(500);
    }
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "12-notifications");
    collectedScreenshots.push(desktop, mobile);
  });
});

test.describe("Evidence Screenshots - Error States", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      try {
        window.localStorage.setItem("landgrant.persona", "admin");
      } catch {
        /* ignore */
      }
    });
  });

  test("404 - Not Found Page", async ({ page }) => {
    await page.goto("/this-page-does-not-exist-404");
    await page.waitForLoadState("networkidle");
    const { desktop, mobile } = await captureResponsiveScreenshots(page, "99-404-error");
    collectedScreenshots.push(desktop, mobile);
    // The app renders an explicit NotFoundPage at unknown routes; previously
    // it silently redirected to `/` which masked broken deep links.
    await expect(page.getByTestId("not-found-page")).toBeVisible();
  });
});
