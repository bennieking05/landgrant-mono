/**
 * Smoke tests against a deployed staging URL (Phase 2).
 * Set PLAYWRIGHT_REMOTE=1, E2E_STAGING_BASE_URL, VITE_API_BASE, and staging credentials.
 */

import { test, expect, type Page, type APIRequestContext } from "@playwright/test";

const REMOTE = process.env.PLAYWRIGHT_REMOTE === "1";
const STAGING_URL = process.env.E2E_STAGING_BASE_URL ?? "";
const API_BASE = process.env.VITE_API_BASE ?? "";
const STAGING_EMAIL = process.env.STAGING_LOGIN_EMAIL ?? "";
const STAGING_PASSWORD = process.env.STAGING_LOGIN_PASSWORD ?? "";

const TOKEN_KEY = "landgrant.jwt";

async function login(page: Page, request: APIRequestContext) {
  const res = await request.post(`${API_BASE}/auth/login`, {
    data: { email: STAGING_EMAIL, password: STAGING_PASSWORD },
  });
  expect(res.ok(), "staging login").toBeTruthy();
  const { access_token: token } = (await res.json()) as { access_token: string };
  await page.addInitScript(
    ([key, value]) => {
      window.sessionStorage.setItem(key, value);
    },
    [TOKEN_KEY, token] as const,
  );
}

test.describe("Staging smoke", () => {
  test.beforeEach(({}, testInfo) => {
    if (
      !REMOTE ||
      !STAGING_URL ||
      !STAGING_EMAIL ||
      !STAGING_PASSWORD ||
      !API_BASE
    ) {
      testInfo.skip(
        true,
        "Need PLAYWRIGHT_REMOTE=1, E2E_STAGING_BASE_URL, VITE_API_BASE, STAGING_LOGIN_EMAIL, STAGING_LOGIN_PASSWORD",
      );
    }
  });

  test("home loads 200", async ({ page, request }) => {
    await login(page, request);
    const r = await page.goto("/", { waitUntil: "domcontentloaded" });
    expect(r?.status()).toBe(200);
    await expect(page.locator("body")).toBeVisible();
  });

  test("workbench loads 200", async ({ page, request }) => {
    await login(page, request);
    const r = await page.goto("/workbench", { waitUntil: "domcontentloaded" });
    expect(r?.status()).toBe(200);
  });
});
