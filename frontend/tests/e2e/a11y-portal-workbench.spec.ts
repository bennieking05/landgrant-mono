import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const API_BASE = process.env.VITE_API_BASE ?? "http://localhost:8050";
const TOKEN_KEY = "landgrant.jwt";
const TEST_EMAIL = "admin@landgrant.local";
const TEST_PASSWORD = "devpass123";

async function staffLogin(page: Page, request: APIRequestContext): Promise<void> {
  const res = await request.post(`${API_BASE}/auth/login`, {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
  });
  expect(res.ok()).toBeTruthy();
  const { access_token: token } = (await res.json()) as { access_token: string };
  await page.addInitScript(
    ([key, value]) => {
      window.sessionStorage.setItem(key, value);
    },
    [TOKEN_KEY, token] as const,
  );
}

async function runAxe(page: Page, route: string) {
  await page.goto(route, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(500);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(
    serious,
    `${route}: serious/critical a11y violations: ${serious.map((v) => v.id).join(", ")}`,
  ).toHaveLength(0);
}

test.describe("Axe WCAG checks", () => {
  test.beforeEach(async ({ page, request }) => {
    await staffLogin(page, request);
  });

  test("portal route", async ({ page }) => {
    await runAxe(page, "/portal?projectId=PRJ-001&parcelId=PARCEL-001");
  });

  test("workbench route", async ({ page }) => {
    await runAxe(page, "/workbench?projectId=PRJ-001&parcelId=PARCEL-001");
  });
});
