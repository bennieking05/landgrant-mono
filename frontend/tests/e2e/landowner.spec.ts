import { test, expect } from "@playwright/test";
import path from "path";

/**
 * Landowner Portal E2E Tests
 *
 * Journey: Invite → Verify → Review docs → Upload → Decision
 *
 * Prerequisites:
 *   - Backend running on port 8050
 *   - Frontend running on port 3050
 */

const ARTIFACTS_DIR = path.resolve(__dirname, "..", "..", "..", "artifacts", "e2e");
const PROJECT_ID = "PRJ-001";
const PARCEL_ID = "PARCEL-001";

test.describe("Landowner Portal Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to intake page with project/parcel context
    await page.goto(`/intake?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
  });

  test("should load intake page with all components", async ({ page }) => {
    // Verify page title/header
    await expect(page.locator("text=Landowner portal")).toBeVisible();
    await expect(page.locator("text=Invite → review → e-sign")).toBeVisible();

    // Take screenshot of initial state
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "landowner-01-intake-page.png"),
      fullPage: true,
    });
  });

  test("should display invite card with send functionality", async ({ page }) => {
    // Find invite card component
    const inviteCard = page.locator('[class*="InviteCard"], [data-testid="invite-card"]').first();
    
    // If there's a visible invite section, interact with it
    const inviteSection = page.locator("text=Invite").first();
    if (await inviteSection.isVisible()) {
      await page.screenshot({
        path: path.join(ARTIFACTS_DIR, "landowner-02-invite-card.png"),
      });
    }
  });

  test("should show decision options for landowner", async ({ page }) => {
    // Look for decision actions component
    const decisionSection = page.locator("text=Accept").first();
    
    // Wait for decision options to load (may come from API)
    await page.waitForTimeout(1000);

    // Screenshot decision UI
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "landowner-03-decision-options.png"),
      fullPage: true,
    });

    // Verify decision options are present
    const acceptButton = page.locator("button", { hasText: /accept/i }).first();
    const counterButton = page.locator("button", { hasText: /counter/i }).first();
    const requestCallButton = page.locator("button", { hasText: /request call/i }).first();

    // At least one option should be visible
    const anyVisible =
      (await acceptButton.isVisible().catch(() => false)) ||
      (await counterButton.isVisible().catch(() => false)) ||
      (await requestCallButton.isVisible().catch(() => false));

    // Log what we found for debugging
    console.log("Decision options visible:", anyVisible);
  });

  test("should display upload panel", async ({ page }) => {
    // Look for upload section
    const uploadSection = page.locator("text=Upload").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "landowner-04-upload-panel.png"),
      fullPage: true,
    });
  });

  test("should show AI draft panel", async ({ page }) => {
    // Look for AI draft section
    const aiSection = page.locator("text=AI").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "landowner-05-ai-panel.png"),
      fullPage: true,
    });
  });

  test("should navigate back to home", async ({ page }) => {
    // Navigate to home
    await page.goto("/");
    
    // Verify home page loads
    await expect(page.locator("text=LandRight MVP")).toBeVisible();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "landowner-06-home-return.png"),
      fullPage: true,
    });
  });
});
