import { test, expect } from "@playwright/test";
import path from "path";
import { isBackendAvailable, SKIP_API_MESSAGE } from "../utils/backend-check";

/**
 * Litigation Case Management E2E Tests
 *
 * Journey: Create case → Update status → Track history → View analytics
 *
 * Prerequisites:
 *   - Backend running on port 8050
 *   - Frontend running on port 3050
 */

const ARTIFACTS_DIR = path.resolve(__dirname, "..", "..", "..", "artifacts", "e2e");
const PROJECT_ID = "PRJ-001";
const PARCEL_ID = "PARCEL-001";
const API_BASE = "http://localhost:8050";

test.describe("Litigation Case Management", () => {
  let createdCaseId: string | null = null;

  test("API: should create a litigation case", async ({ request }) => {
    const backendUp = await isBackendAvailable();
    if (!backendUp) {
      test.skip(true, SKIP_API_MESSAGE);
      return;
    }
    const response = await request.post(`${API_BASE}/litigation`, {
      headers: {
        "X-Persona": "in_house_counsel",
        "Content-Type": "application/json",
      },
      data: {
        parcel_id: PARCEL_ID,
        project_id: PROJECT_ID,
        court: "District Court of Travis County",
        court_county: "Travis",
        is_quick_take: false,
      },
    });

    // Accept 200 (created) or 422 (already exists from previous test run)
    expect([200, 422]).toContain(response.status());
    const data = await response.json();
    
    if (response.status() === 200) {
      expect(data.case_id).toBeTruthy();
      createdCaseId = data.case_id;
      console.log(`Created litigation case: ${createdCaseId}`);
    } else {
      // Case already exists - try to get existing case
      const listResponse = await request.get(`${API_BASE}/litigation?parcel_id=${PARCEL_ID}`, {
        headers: { "X-Persona": "in_house_counsel" },
      });
      if (listResponse.status() === 200) {
        const list = await listResponse.json();
        if (list.items?.length > 0) {
          createdCaseId = list.items[0].id;
          console.log(`Using existing litigation case: ${createdCaseId}`);
        }
      }
    }
  });

  test("API: should create a quick-take case", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    // Use existing parcel from seed data
    const response = await request.post(`${API_BASE}/litigation`, {
      headers: {
        "X-Persona": "in_house_counsel",
        "Content-Type": "application/json",
      },
      data: {
        parcel_id: "PARCEL-002",  // Use existing parcel
        project_id: PROJECT_ID,
        court: "District Court",
        court_county: "Harris",
        is_quick_take: true,
        cause_number: `2026-CV-${Math.floor(Math.random() * 100000)}`,
      },
    });

    // Accept 200 (created) or 422 (already exists)
    expect([200, 422]).toContain(response.status());
    if (response.status() === 200) {
      const data = await response.json();
      expect(data.case_id).toBeTruthy();
      expect(data.status).toBe("not_filed");
      console.log(`Created quick-take case: ${data.case_id}`);
    } else {
      console.log("Quick-take case already exists for parcel");
    }
  });

  test("API: should list litigation cases with filters", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    const response = await request.get(
      `${API_BASE}/litigation?project_id=${PROJECT_ID}`,
      { headers: { "X-Persona": "in_house_counsel" } }
    );

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data.items)).toBe(true);
    console.log(`Found ${data.items.length} litigation cases`);
  });

  test("API: should update case status through workflow", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    // Use existing parcel from seed data
    const createResponse = await request.post(`${API_BASE}/litigation`, {
      headers: {
        "X-Persona": "in_house_counsel",
        "Content-Type": "application/json",
      },
      data: {
        parcel_id: "PARCEL-003",  // Use existing parcel
        project_id: PROJECT_ID,
        court: "County Court",
      },
    });
    
    // Accept 200 (created) or 422 (already exists)
    if (createResponse.status() === 422) {
      // Get existing case
      const listResponse = await request.get(`${API_BASE}/litigation?parcel_id=PARCEL-003`, {
        headers: { "X-Persona": "in_house_counsel" },
      });
      const list = await listResponse.json();
      if (list.items.length === 0) {
        test.skip(true, "Cannot find existing case for parcel");
        return;
      }
    }
    
    const created = await createResponse.json();
    const caseId = created.case_id || created.detail;
    if (!caseId || caseId === "active_case_exists_for_parcel") {
      // Skip if can't get case ID
      test.skip(true, "Cannot get case ID for status update test");
      return;
    }

    // Update to filed
    const filedResponse = await request.put(`${API_BASE}/litigation/${caseId}`, {
      headers: {
        "X-Persona": "in_house_counsel",
        "Content-Type": "application/json",
      },
      data: {
        status: "filed",
        filing_date: new Date().toISOString(),
      },
    });
    expect(filedResponse.status()).toBe(200);

    // Update to served
    const servedResponse = await request.put(`${API_BASE}/litigation/${caseId}`, {
      headers: {
        "X-Persona": "outside_counsel",
        "Content-Type": "application/json",
      },
      data: {
        status: "served",
        service_date: new Date().toISOString(),
      },
    });
    expect(servedResponse.status()).toBe(200);

    // Verify status
    const getResponse = await request.get(`${API_BASE}/litigation/${caseId}`, {
      headers: { "X-Persona": "in_house_counsel" },
    });
    const updated = await getResponse.json();
    expect(updated.status).toBe("served");
  });

  test("API: should get case status history", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    // Use existing parcel from seed data
    const createResponse = await request.post(`${API_BASE}/litigation`, {
      headers: {
        "X-Persona": "in_house_counsel",
        "Content-Type": "application/json",
      },
      data: {
        parcel_id: "PARCEL-004",  // Use existing parcel
        project_id: PROJECT_ID,
        court: "State Court",
      },
    });
    
    let caseId: string;
    if (createResponse.status() === 422) {
      // Get existing case
      const listResponse = await request.get(`${API_BASE}/litigation?parcel_id=PARCEL-004`, {
        headers: { "X-Persona": "in_house_counsel" },
      });
      const list = await listResponse.json();
      if (list.items.length === 0) {
        test.skip(true, "Cannot find existing case for parcel");
        return;
      }
      caseId = list.items[0].id;
    } else {
      const created = await createResponse.json();
      caseId = created.case_id;
    }

    // Update status
    await request.put(`${API_BASE}/litigation/${caseId}`, {
      headers: {
        "X-Persona": "in_house_counsel",
        "Content-Type": "application/json",
      },
      data: { status: "filed", status_notes: "Filed petition with court" },
    });

    // Get history
    const historyResponse = await request.get(
      `${API_BASE}/litigation/${caseId}/history`,
      { headers: { "X-Persona": "in_house_counsel" } }
    );

    expect(historyResponse.status()).toBe(200);
    const history = await historyResponse.json();
    expect(Array.isArray(history.history)).toBe(true);
    console.log(`History entries: ${history.history.length}`);
  });

  test("API: should get litigation analytics", async ({ request }) => {
    if (!(await isBackendAvailable())) { test.skip(true, SKIP_API_MESSAGE); return; }
    const response = await request.get(
      `${API_BASE}/litigation/analytics/summary?project_id=${PROJECT_ID}`,
      { headers: { "X-Persona": "in_house_counsel" } }
    );

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.status_breakdown).toBeDefined();
    expect(typeof data.quick_take_count).toBe("number");
    console.log(`Analytics: ${JSON.stringify(data)}`);
  });

  test("API: complaint-parcels validate with JWT", async ({ request }) => {
    if (!(await isBackendAvailable())) {
      test.skip(true, SKIP_API_MESSAGE);
      return;
    }
    const loginRes = await request.post(`${API_BASE}/auth/login`, {
      data: { email: "counsel@example.com", password: "devpass123" },
    });
    if (!loginRes.ok()) {
      test.skip(true, "counsel login failed");
      return;
    }
    const { access_token: token } = (await loginRes.json()) as { access_token: string };
    const headers = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
    const res = await request.post(`${API_BASE}/litigation/complaint-parcels/validate`, {
      headers,
      data: { project_id: PROJECT_ID, parcel_ids: ["PARCEL-001", "PARCEL-002"] },
    });
    expect(res.status()).toBe(200);
    const body = (await res.json()) as { ok: boolean; errors: string[] };
    expect(body.ok).toBe(true);
    expect(body.errors ?? []).toEqual([]);
  });

  test("API: litigation tracks with JWT", async ({ request }) => {
    if (!(await isBackendAvailable())) {
      test.skip(true, SKIP_API_MESSAGE);
      return;
    }
    const loginRes = await request.post(`${API_BASE}/auth/login`, {
      data: { email: "counsel@example.com", password: "devpass123" },
    });
    if (!loginRes.ok()) {
      test.skip(true, "counsel login failed");
      return;
    }
    const { access_token: token } = (await loginRes.json()) as { access_token: string };
    const headers = { Authorization: `Bearer ${token}` };
    const listRes = await request.get(`${API_BASE}/litigation?parcel_id=${PARCEL_ID}`, { headers });
    expect(listRes.status()).toBe(200);
    const list = (await listRes.json()) as { items: Array<{ id: string }> };
    if (!list.items?.length) {
      test.skip(true, "no litigation case for parcel");
      return;
    }
    const caseId = list.items[0].id;
    const tracksRes = await request.get(`${API_BASE}/litigation/${caseId}/tracks`, { headers });
    expect(tracksRes.status()).toBe(200);
    const tracks = (await tracksRes.json()) as { tx: unknown; in: unknown };
    expect(tracks.tx).toBeDefined();
    expect(tracks.in).toBeDefined();
  });
});
