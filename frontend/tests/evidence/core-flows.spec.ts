/**
 * Core Flows Evidence Screenshot Capture
 * 
 * This test file captures screenshots for all core user flows.
 * Used for regression evidence and visual verification.
 * 
 * Run: npm run test:evidence
 * 
 * Environment variables:
 *   FEATURE_NAME - Name of feature/branch (default: 'regression')
 *   EVIDENCE_TS  - Timestamp for folder (default: auto-generated)
 */

import { test, expect } from '@playwright/test';
import {
  captureResponsiveScreenshots,
  captureScreenshot,
  generateEvidenceSummary,
  printEvidenceSummary,
  VIEWPORTS,
} from '../utils/screenshot';

const collectedScreenshots: string[] = [];

test.describe('Evidence Screenshots - Core Flows', () => {
  
  test.beforeEach(async ({ page }) => {
    // Set desktop viewport as default
    await page.setViewportSize(VIEWPORTS.desktop);
  });

  test.afterAll(async () => {
    // Print evidence summary after all tests
    const summary = generateEvidenceSummary(collectedScreenshots);
    printEvidenceSummary(summary, collectedScreenshots.length / 2); // Divide by 2 for desktop+mobile pairs
  });

  test('01 - Homepage / Dashboard', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '01-homepage');
    collectedScreenshots.push(desktop, mobile);
    
    // Basic assertion
    await expect(page).toHaveTitle(/LandRight|Dashboard/i);
  });

  test('02 - Case List View', async ({ page }) => {
    await page.goto('/cases');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '02-case-list');
    collectedScreenshots.push(desktop, mobile);
  });

  test('03 - Case Detail View', async ({ page }) => {
    // Navigate to cases first, then try to click into one
    await page.goto('/cases');
    await page.waitForLoadState('networkidle');
    
    // Try to find and click a case, or just capture the list
    const caseLink = page.locator('[data-testid="case-row"]').first();
    if (await caseLink.isVisible().catch(() => false)) {
      await caseLink.click();
      await page.waitForLoadState('networkidle');
    }
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '03-case-detail');
    collectedScreenshots.push(desktop, mobile);
  });

  test('04 - Parcel View', async ({ page }) => {
    await page.goto('/parcels');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '04-parcel-view');
    collectedScreenshots.push(desktop, mobile);
  });

  test('05 - Intake Form', async ({ page }) => {
    await page.goto('/intake');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '05-intake-form');
    collectedScreenshots.push(desktop, mobile);
  });

  test('06 - Settlement Predictor', async ({ page }) => {
    await page.goto('/settlement');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '06-settlement-predictor');
    collectedScreenshots.push(desktop, mobile);
  });

  test('07 - AI Copilot Panel', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Try to open copilot if there's a button
    const copilotBtn = page.locator('[data-testid="copilot-toggle"], button:has-text("Copilot"), button:has-text("AI")').first();
    if (await copilotBtn.isVisible().catch(() => false)) {
      await copilotBtn.click();
      await page.waitForTimeout(500);
    }
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '07-copilot-panel');
    collectedScreenshots.push(desktop, mobile);
  });

  test('08 - Task Manager', async ({ page }) => {
    await page.goto('/tasks');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '08-task-manager');
    collectedScreenshots.push(desktop, mobile);
  });

  test('09 - Notifications', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Try to open notifications if there's a bell
    const notifBell = page.locator('[data-testid="notification-bell"], button[aria-label*="notification"]').first();
    if (await notifBell.isVisible().catch(() => false)) {
      await notifBell.click();
      await page.waitForTimeout(500);
    }
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '09-notifications');
    collectedScreenshots.push(desktop, mobile);
  });

  test('10 - Documents / Templates', async ({ page }) => {
    await page.goto('/templates');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '10-templates');
    collectedScreenshots.push(desktop, mobile);
  });

  test('11 - AI Decisions Dashboard', async ({ page }) => {
    await page.goto('/ai-decisions');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '11-ai-decisions');
    collectedScreenshots.push(desktop, mobile);
  });

  test('12 - Predictions', async ({ page }) => {
    await page.goto('/predictions');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '12-predictions');
    collectedScreenshots.push(desktop, mobile);
  });

});

test.describe('Evidence Screenshots - Error States', () => {

  test('404 - Not Found Page', async ({ page }) => {
    await page.goto('/this-page-does-not-exist-404');
    await page.waitForLoadState('networkidle');
    
    const { desktop, mobile } = await captureResponsiveScreenshots(page, '99-404-error');
    collectedScreenshots.push(desktop, mobile);
  });

});
