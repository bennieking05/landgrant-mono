/**
 * Full-page screenshots per authenticated route (Phase 2 gallery).
 * With CLEAR_GALLERY_DB=1 + global-setup, DB is truncated for empty-ish UI.
 */

import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import fs from "fs";
import path from "path";

const API_BASE = process.env.VITE_API_BASE ?? "http://localhost:8050";
const TOKEN_KEY = "landgrant.jwt";
const TEST_EMAIL = "admin@landgrant.local";
const TEST_PASSWORD = "devpass123";

const GALLERY_DIR = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "artifacts",
  "e2e",
  "empty-state-gallery",
);

const ROUTES = [
  "/",
  "/intake",
  "/workbench",
  "/counsel",
  "/ops",
  "/firm-admin",
  "/admin",
] as const;

async function login(page: Page, request: APIRequestContext): Promise<void> {
  const res = await request.post(`${API_BASE}/auth/login`, {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
  });
  expect(res.ok(), "login should succeed for gallery").toBeTruthy();
  const { access_token: token } = (await res.json()) as { access_token: string };
  await page.addInitScript(
    ([key, value]) => {
      window.sessionStorage.setItem(key, value);
    },
    [TOKEN_KEY, token] as const,
  );
}

test.describe.configure({ mode: "serial" });

test.describe("Empty-state route gallery", () => {
  test.beforeAll(() => {
    fs.mkdirSync(GALLERY_DIR, { recursive: true });
  });

  test.beforeEach(async ({ page, request }) => {
    await login(page, request);
  });

  for (const route of ROUTES) {
    test(`screenshot ${route}`, async ({ page }) => {
      const safe = route.replace(/\//g, "_") || "root";
      const response = await page.goto(route, { waitUntil: "domcontentloaded" });
      expect(response, `navigation ${route}`).toBeTruthy();
      expect(response!.status(), `${route} should return 200`).toBe(200);
      await page.waitForTimeout(800);
      const out = path.join(GALLERY_DIR, `gallery${safe}.png`);
      await page.screenshot({ path: out, fullPage: true });
    });
  }
});
