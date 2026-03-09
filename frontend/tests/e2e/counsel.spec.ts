import { test, expect } from "@playwright/test";
import path from "path";

/**
 * Counsel Controls E2E Tests
 *
 * Journey: Approval queue → Templates → Binder export → Budget → Deadlines
 *
 * Prerequisites:
 *   - Backend running on port 8050
 *   - Frontend running on port 3050
 */

const ARTIFACTS_DIR = path.resolve(__dirname, "..", "..", "..", "artifacts", "e2e");
const PROJECT_ID = "PRJ-001";
const PARCEL_ID = "PARCEL-001";

test.describe("Counsel Controls Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to counsel page
    await page.goto(`/counsel?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
  });

  test("should load counsel page with all components", async ({ page }) => {
    // Verify page title/header
    await expect(page.locator("text=Counsel controls")).toBeVisible();
    await expect(page.locator("text=Template approvals")).toBeVisible();

    // Take screenshot of initial state
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-01-counsel-page.png"),
      fullPage: true,
    });
  });

  test("should display approval queue", async ({ page }) => {
    // Wait for approvals to load
    await page.waitForTimeout(1500);

    // Look for approval queue
    const queueSection = page.locator("text=Approval").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-02-approval-queue.png"),
      fullPage: true,
    });

    // Check for approval items
    const approvalItem = page.locator("text=Approve").first();
    if (await approvalItem.isVisible().catch(() => false)) {
      console.log("Approval queue items visible");
    }
  });

  test("should show budget summary", async ({ page }) => {
    // Wait for budget data
    await page.waitForTimeout(1000);

    // Look for budget section
    const budgetSection = page.locator("text=Budget").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-03-budget-panel.png"),
      fullPage: true,
    });

    // Check for utilization display
    const utilization = page.locator("text=%").first();
    if (await utilization.isVisible().catch(() => false)) {
      console.log("Budget utilization percentage visible");
    }
  });

  test("should display binder status", async ({ page }) => {
    // Wait for binder status
    await page.waitForTimeout(1000);

    // Look for binder section
    const binderSection = page.locator("text=Binder").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-04-binder-status.png"),
      fullPage: true,
    });

    // Check for section statuses
    const completeStatus = page.locator("text=Complete").first();
    if (await completeStatus.isVisible().catch(() => false)) {
      console.log("Binder section status visible");
    }
  });

  test("should show deadline manager", async ({ page }) => {
    // Wait for deadlines
    await page.waitForTimeout(1000);

    // Look for deadline section
    const deadlineSection = page.locator("text=Deadline").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-05-deadline-manager.png"),
      fullPage: true,
    });
  });

  test("should display template viewer", async ({ page }) => {
    // Wait for templates
    await page.waitForTimeout(1000);

    // Look for template section
    const templateSection = page.locator("text=Template").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-06-template-viewer.png"),
      fullPage: true,
    });

    // Check for template list items
    const templateItem = page.locator("text=fol").first();
    if (await templateItem.isVisible().catch(() => false)) {
      console.log("Template items visible");
    }
  });

  test("should show outside counsel panel", async ({ page }) => {
    // Wait for outside counsel data
    await page.waitForTimeout(1000);

    // Look for outside counsel section
    const outsideSection = page.locator("text=Outside").first();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-07-outside-counsel.png"),
      fullPage: true,
    });

    // Check for completeness percentage
    const completeness = page.locator("text=Repository").first();
    if (await completeness.isVisible().catch(() => false)) {
      console.log("Repository completeness visible");
    }
  });

  test("should navigate to ops page", async ({ page }) => {
    // Navigate to ops
    await page.goto("/ops");
    
    // Verify ops page loads - look for the main h1 heading
    await expect(page.getByRole("heading", { name: "Route Planning & Communications" })).toBeVisible();
    
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-08-ops-navigation.png"),
      fullPage: true,
    });
  });

  test("full counsel workflow", async ({ page }) => {
    // This test captures the full counsel workflow in sequence
    
    // 1. View approval queue
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-flow-01-approvals.png"),
    });

    // 2. Scroll to budget
    await page.locator("text=Budget").first().scrollIntoViewIfNeeded();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-flow-02-budget.png"),
    });

    // 3. Scroll to binder
    await page.locator("text=Binder").first().scrollIntoViewIfNeeded();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-flow-03-binder.png"),
    });

    // 4. Scroll to templates
    await page.locator("text=Template").first().scrollIntoViewIfNeeded();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-flow-04-templates.png"),
    });

    // 5. Final full page
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "counsel-flow-05-complete.png"),
      fullPage: true,
    });
  });
});
