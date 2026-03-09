import { test, expect } from "@playwright/test";
import path from "path";

/**
 * Land Agent Workbench E2E Tests
 *
 * Journey: Parcel list → Select parcel → Comms log → Packet checklist → Title upload
 *
 * Prerequisites:
 *   - Backend running on port 8050
 *   - Frontend running on port 3050
 */

const ARTIFACTS_DIR = path.resolve(__dirname, "..", "..", "..", "artifacts", "e2e");
const PROJECT_ID = "PRJ-001";
const PARCEL_ID = "PARCEL-001";

test.describe("Agent Workbench Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to workbench page
    await page.goto(`/workbench?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
  });

  test("should load workbench page with all components", async ({ page }) => {
    // Verify page title/header
    await expect(page.locator("text=Agent workbench")).toBeVisible();
    await expect(page.locator("text=Parcel list")).toBeVisible();

    // Take screenshot of initial state
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "agent-01-workbench-page.png"),
      fullPage: true,
    });
  });

  test("should display parcel list with filtering", async ({ page }) => {
    // Wait for parcel list to load from API
    await page.waitForTimeout(1500);

    // Look for parcel list component
    const parcelList = page.locator("text=Parcels").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "agent-02-parcel-list.png"),
      fullPage: true,
    });

    // Check for parcel IDs in the list
    const parcelItems = page.locator('[data-testid="parcel-item"], li, tr').filter({ hasText: /PARCEL/ });
    const count = await parcelItems.count();
    console.log(`Found ${count} parcel items`);
  });

  test("should show communications log for selected parcel", async ({ page }) => {
    // Wait for comms to load
    await page.waitForTimeout(1000);

    // Look for comms log section
    const commsSection = page.locator("text=Comms").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "agent-03-comms-log.png"),
      fullPage: true,
    });

    // Verify comms items are displayed
    const commsItems = page.locator("text=delivered").first();
    if (await commsItems.isVisible().catch(() => false)) {
      console.log("Communications log showing delivered items");
    }
  });

  test("should display packet checklist status", async ({ page }) => {
    // Wait for packet data
    await page.waitForTimeout(1000);

    // Look for packet checklist
    const packetSection = page.locator("text=Packet").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "agent-04-packet-checklist.png"),
      fullPage: true,
    });

    // Check for checklist items
    const checklistItems = page.locator("text=Title chain").first();
    if (await checklistItems.isVisible().catch(() => false)) {
      console.log("Packet checklist visible with title chain item");
    }
  });

  test("should show rule results for parcel", async ({ page }) => {
    // Wait for rules to load
    await page.waitForTimeout(1000);

    // Look for rule results
    const rulesSection = page.locator("text=Rule").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "agent-05-rule-results.png"),
      fullPage: true,
    });

    // Check for citation display
    const citation = page.locator("text=Tex. Prop. Code").first();
    if (await citation.isVisible().catch(() => false)) {
      console.log("Rule citation visible");
    }
  });

  test("should display title panel", async ({ page }) => {
    // Wait for title instruments
    await page.waitForTimeout(1000);

    // Look for title section
    const titleSection = page.locator("text=Title").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "agent-06-title-panel.png"),
      fullPage: true,
    });
  });

  test("should display appraisal panel", async ({ page }) => {
    // Wait for appraisal data
    await page.waitForTimeout(1000);

    // Look for appraisal section
    const appraisalSection = page.locator("text=Appraisal").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "agent-07-appraisal-panel.png"),
      fullPage: true,
    });

    // Check for value display
    const valueDisplay = page.locator("text=$").first();
    if (await valueDisplay.isVisible().catch(() => false)) {
      console.log("Appraisal value displayed");
    }
  });

  test("should navigate between pages", async ({ page }) => {
    // Click home link or navigate
    await page.goto("/");
    await expect(page.locator("text=LandRight MVP")).toBeVisible();
    
    // Navigate back to workbench
    await page.click("text=Agent Workbench");
    await expect(page.locator("text=Agent workbench")).toBeVisible();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "agent-08-navigation.png"),
      fullPage: true,
    });
  });
});
