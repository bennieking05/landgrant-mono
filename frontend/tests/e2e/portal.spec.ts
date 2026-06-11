import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import path from "path";

/**
 * Landowner `/portal` route — staff-only tools must not appear here.
 *
 * Uses seeded `owner@example.com` (LANDOWNER-001) when the dev DB seed has run.
 */

const ARTIFACTS_DIR = path.resolve(__dirname, "..", "..", "..", "artifacts", "e2e");
const PROJECT_ID = "PRJ-001";
const PARCEL_ID = "PARCEL-001";
const API_BASE = process.env.VITE_API_BASE ?? "http://localhost:8050";
const TOKEN_KEY = "landgrant.jwt";

async function login(page: Page, request: APIRequestContext, email: string, password: string) {
  const res = await request.post(`${API_BASE}/auth/login`, {
    data: { email, password },
  });
  expect(res.ok(), `login failed for ${email}`).toBeTruthy();
  const { access_token: token } = (await res.json()) as { access_token: string };
  await page.addInitScript(
    ([key, value]) => {
      window.sessionStorage.setItem(key, value);
    },
    [TOKEN_KEY, token] as const,
  );
}

test.describe("Landowner portal route", () => {
  test("owner can open /portal and does not see staff intake", async ({ page, request }) => {
    const loginRes = await request.post(`${API_BASE}/auth/login`, {
      data: { email: "owner@example.com", password: "devpass123" },
    });
    if (!loginRes.ok()) {
      test.skip(true, "owner@example.com not in DB (re-seed dev data to enable)");
      return;
    }
    const { access_token: token } = (await loginRes.json()) as { access_token: string };
    await page.addInitScript(
      ([key, value]) => {
        window.sessionStorage.setItem(key, value);
      },
      [TOKEN_KEY, token] as const,
    );
    await page.goto(`/portal?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);

    await expect(page.locator("text=Landowner portal")).toBeVisible();
    await expect(page.locator("text=Staff intake")).toHaveCount(0);
    await expect(page.locator("text=Agent Tools")).toHaveCount(0);

    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "portal-01-landowner.png"),
      fullPage: true,
    });
  });

  test("platform admin can open /portal for smoke (same shell)", async ({ page, request }) => {
    await login(page, request, "admin@landgrant.local", "devpass123");
    await page.goto(`/portal?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
    await expect(page.locator("text=Landowner portal")).toBeVisible();
    await expect(page.locator("text=Staff intake")).toHaveCount(0);
  });
});
