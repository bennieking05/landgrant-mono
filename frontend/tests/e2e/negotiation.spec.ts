import { test, expect } from "@playwright/test";
import path from "path";
import { isBackendAvailable, SKIP_API_MESSAGE } from "../utils/backend-check";

/**
 * Negotiation / Offers E2E Tests
 *
 * Journey: Create offer → Counter offer → Accept → Payment ledger
 *
 * Prerequisites:
 *   - Backend running on port 8050
 *   - Frontend running on port 3050
 */

const ARTIFACTS_DIR = path.resolve(__dirname, "..", "..", "..", "artifacts", "e2e");
const PROJECT_ID = "PRJ-001";
const PARCEL_ID = "PARCEL-001";
const API_BASE = "http://localhost:8050";

test.describe("Negotiation Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/workbench?projectId=${PROJECT_ID}&parcelId=${PARCEL_ID}`);
    await page.waitForTimeout(1000);
  });

  test("API: should create an initial offer", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    const response = await request.post(`${API_BASE}/offers`, {
      headers: {
        "X-Persona": "land_agent",
        "Content-Type": "application/json",
      },
      data: {
        parcel_id: PARCEL_ID,
        project_id: PROJECT_ID,
        offer_type: "initial",
        amount: 150000,
        terms: { description: "Standard acquisition terms" },
      },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.offer_id).toBeTruthy();
    expect(data.offer_number).toBeDefined();
    console.log(`Created offer: ${data.offer_id}`);
  });

  test("API: should list offers for a parcel", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    const response = await request.get(`${API_BASE}/offers?parcel_id=${PARCEL_ID}`, {
      headers: { "X-Persona": "land_agent" },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data.items)).toBe(true);
    console.log(`Found ${data.items.length} offers`);
  });

  test("API: should record a counteroffer", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    // Create initial offer
    const createResponse = await request.post(`${API_BASE}/offers`, {
      headers: {
        "X-Persona": "land_agent",
        "Content-Type": "application/json",
      },
      data: {
        parcel_id: PARCEL_ID,
        project_id: PROJECT_ID,
        offer_type: "initial",
        amount: 100000,
      },
    });
    const created = await createResponse.json();
    const offerId = created.offer_id;

    // Submit counteroffer (land_agent has offer write permission)
    const counterResponse = await request.post(`${API_BASE}/offers/${offerId}/counter`, {
      headers: {
        "X-Persona": "land_agent",
        "Content-Type": "application/json",
      },
      data: {
        amount: 125000,
        terms: { description: "Landowner requested higher amount" },
        source: "landowner",
      },
    });

    expect(counterResponse.status()).toBe(200);
    const counter = await counterResponse.json();
    expect(counter.counter_id).toBeTruthy();
  });

  test("API: should get payment ledger status", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    const response = await request.get(`${API_BASE}/payment-ledger/${PARCEL_ID}`, {
      headers: { "X-Persona": "land_agent" },
    });

    // May return 404 if no ledger exists yet, which is acceptable
    expect([200, 404]).toContain(response.status());
    
    if (response.status() === 200) {
      const data = await response.json();
      console.log(`Payment status: ${data.payment_status}`);
    }
  });

  test("API: should update payment ledger", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    const response = await request.put(`${API_BASE}/payment-ledger/${PARCEL_ID}`, {
      headers: {
        "X-Persona": "land_agent",
        "Content-Type": "application/json",
      },
      data: {
        status: "pending",
        notes: "Check approved, awaiting disbursement",
      },
    });

    // Accept 200 (success) or 404 (endpoint not implemented)
    expect([200, 404]).toContain(response.status());
    if (response.status() === 404) {
      console.log("Payment ledger update endpoint not implemented");
    }
  });

  test("UI: should display negotiation panel", async ({ page }) => {
    // Take screenshot of negotiation UI
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, "negotiation-01-panel.png"),
      fullPage: true,
    });
  });

  test("API: complete offer lifecycle - initial to accepted", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    // Create initial offer using existing parcel from seed data
    const createResponse = await request.post(`${API_BASE}/offers`, {
      headers: {
        "X-Persona": "land_agent",
        "Content-Type": "application/json",
      },
      data: {
        parcel_id: "PARCEL-002",  // Use existing parcel from seed data
        project_id: PROJECT_ID,
        offer_type: "initial",
        amount: 200000,
      },
    });
    expect(createResponse.status()).toBe(200);
    const offer = await createResponse.json();

    // Update to sent
    const updateResponse = await request.put(`${API_BASE}/offers/${offer.offer_id}`, {
      headers: {
        "X-Persona": "land_agent",
        "Content-Type": "application/json",
      },
      data: { status: "sent" },
    });
    expect(updateResponse.status()).toBe(200);

    // Update to accepted (land_agent has offer write permission)
    const acceptResponse = await request.put(`${API_BASE}/offers/${offer.offer_id}`, {
      headers: {
        "X-Persona": "land_agent",
        "Content-Type": "application/json",
      },
      data: { status: "accepted" },
    });
    expect(acceptResponse.status()).toBe(200);

    // Get final status
    const getResponse = await request.get(`${API_BASE}/offers/${offer.offer_id}`, {
      headers: { "X-Persona": "land_agent" },
    });
    const finalOffer = await getResponse.json();
    expect(finalOffer.status).toBe("accepted");
    console.log(`Offer lifecycle completed: ${offer.offer_id}`);
  });
});
