# UAT Regression Checklist

This document provides a human-led regression test checklist for User Acceptance Testing (UAT) before each release.

## How to Use

1. **Before Testing**: Ensure backend (port 8050) and frontend (port 3050) are running
2. **Execute Tests**: Follow each test case step-by-step
3. **Record Results**: Check the Pass/Fail box and add notes for any deviations
4. **Report Issues**: Create tickets for any failures with test case ID reference

### Environment Setup

```bash
# Terminal 1: Start backend
cd backend && uvicorn app.main:app --reload --port 8050

# Terminal 2: Start frontend
cd frontend && npm run dev

# Verify health
curl http://localhost:8050/health/live
```

### Test Data

| Entity | ID | Description |
|--------|-----|-------------|
| Project | PRJ-001 | Utility Corridor Expansion |
| Parcel | PARCEL-001 | Negotiation stage, risk=40 |
| Parcel | PARCEL-002 | Intake stage, risk=75 |
| Owner | OWNER-001 | Riverbend Farms LLC |
| Counsel | COUNSEL-001 | counsel@example.com |
| Agent | AGENT-001 | agent@example.com |

---

## P0 - Release Blockers

These tests MUST pass before any release. Failures block deployment.

### UAT-001: Health Endpoints Respond

| Field | Value |
|-------|-------|
| **Objective** | Verify all health endpoints return 200 OK |
| **Preconditions** | Backend running on port 8050 |
| **Priority** | P0 |

**Steps:**

- [ ] 1. Open terminal
- [ ] 2. Execute: `curl -s http://localhost:8050/health/live`
- [ ] 3. Verify response contains `{"status": "ok"}` or similar success indicator
- [ ] 4. Execute: `curl -s http://localhost:8050/health/invite`
- [ ] 5. Verify response is 200 OK
- [ ] 6. Execute: `curl -s http://localhost:8050/health/esign`
- [ ] 7. Verify response is 200 OK

**Expected Output:**
- All three endpoints return HTTP 200
- Response bodies indicate healthy status

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-002: RBAC - Counsel Template Access

| Field | Value |
|-------|-------|
| **Objective** | Verify only in_house_counsel can access templates |
| **Preconditions** | Backend running |
| **Priority** | P0 |

**Steps:**

- [ ] 1. Execute: `curl -s -H "X-Persona: in_house_counsel" http://localhost:8050/templates`
- [ ] 2. Verify response is HTTP 200 with template list
- [ ] 3. Execute: `curl -s -w "%{http_code}" -H "X-Persona: outside_counsel" http://localhost:8050/templates`
- [ ] 4. Verify response is HTTP 403 Forbidden
- [ ] 5. Execute: `curl -s -w "%{http_code}" -H "X-Persona: land_agent" http://localhost:8050/templates`
- [ ] 6. Verify response is HTTP 403 Forbidden

**Expected Output:**
- in_house_counsel: 200 OK with template data
- outside_counsel: 403 Forbidden
- land_agent: 403 Forbidden

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-003: RBAC - Binder Export Authorization

| Field | Value |
|-------|-------|
| **Objective** | Verify binder export is restricted to counsel |
| **Preconditions** | Backend running |
| **Priority** | P0 |

**Steps:**

- [ ] 1. Execute: `curl -s -X POST -H "X-Persona: in_house_counsel" http://localhost:8050/workflows/binder/export`
- [ ] 2. Verify response is HTTP 200 with `bundle_id` in response
- [ ] 3. Execute: `curl -s -w "%{http_code}" -X POST -H "X-Persona: land_agent" http://localhost:8050/workflows/binder/export`
- [ ] 4. Verify response is HTTP 403 Forbidden

**Expected Output:**
- in_house_counsel: 200 OK, response contains `{"bundle_id": "..."}`
- land_agent: 403 Forbidden

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-004: Portal Decision Options Access

| Field | Value |
|-------|-------|
| **Objective** | Verify landowner can access decision options, agent cannot |
| **Preconditions** | Backend running |
| **Priority** | P0 |

**Steps:**

- [ ] 1. Execute: `curl -s -H "X-Persona: landowner" http://localhost:8050/portal/decision/options`
- [ ] 2. Verify response is HTTP 200
- [ ] 3. Execute: `curl -s -w "%{http_code}" -H "X-Persona: land_agent" http://localhost:8050/portal/decision/options`
- [ ] 4. Verify response is HTTP 403 Forbidden

**Expected Output:**
- landowner: 200 OK with decision options
- land_agent: 403 Forbidden

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-005: Communications Log Access

| Field | Value |
|-------|-------|
| **Objective** | Verify agent can view comms, landowner cannot |
| **Preconditions** | Backend running, PARCEL-001 exists with communications |
| **Priority** | P0 |

**Steps:**

- [ ] 1. Execute: `curl -s -H "X-Persona: land_agent" "http://localhost:8050/communications?parcel_id=PARCEL-001"`
- [ ] 2. Verify response is HTTP 200 with communication records
- [ ] 3. Execute: `curl -s -w "%{http_code}" -H "X-Persona: landowner" "http://localhost:8050/communications?parcel_id=PARCEL-001"`
- [ ] 4. Verify response is HTTP 403 Forbidden

**Expected Output:**
- land_agent: 200 OK with communications array
- landowner: 403 Forbidden

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-006: Rules Engine Fires for High Value Parcel

| Field | Value |
|-------|-------|
| **Objective** | Verify rules engine evaluates correctly for TX jurisdiction |
| **Preconditions** | Backend running |
| **Priority** | P0 |

**Steps:**

- [ ] 1. Execute:
```bash
curl -s -X POST -H "Content-Type: application/json" \
  -H "X-Persona: in_house_counsel" \
  http://localhost:8050/rules/evaluate \
  -d '{"jurisdiction": "tx", "payload": {"parcel.assessed_value": 300000, "case.dispute_level": "HIGH"}}'
```
- [ ] 2. Verify response contains rule results
- [ ] 3. Verify at least one rule "fired" (check for `"fired": true` in response)

**Expected Output:**
- HTTP 200
- Response contains array of rule results
- At least one rule has `fired: true`

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

## P1 - Important Flows

These tests are important but do not block deployment. Failures should be tracked as high-priority bugs.

### UAT-007: Frontend Loads Successfully

| Field | Value |
|-------|-------|
| **Objective** | Verify frontend application loads without errors |
| **Preconditions** | Frontend running on port 3050 |
| **Priority** | P1 |

**Steps:**

- [ ] 1. Open browser to `http://localhost:3050`
- [ ] 2. Verify page loads without JavaScript errors (check browser console)
- [ ] 3. Verify main navigation is visible
- [ ] 4. Verify no "Loading..." spinners stuck indefinitely

**Expected Output:**
- Page renders completely
- No console errors
- Navigation elements visible

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-008: Case Details Endpoint

| Field | Value |
|-------|-------|
| **Objective** | Verify case/parcel details can be retrieved |
| **Preconditions** | Backend running, PARCEL-001 exists |
| **Priority** | P1 |

**Steps:**

- [ ] 1. Execute: `curl -s -H "X-Persona: land_agent" http://localhost:8050/cases/PARCEL-001`
- [ ] 2. Verify response is HTTP 200
- [ ] 3. Verify response contains parcel details (id, stage, risk_score)

**Expected Output:**
- HTTP 200
- Response includes `id`, `stage`, `risk_score` fields

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-009: Workflow Approvals Access

| Field | Value |
|-------|-------|
| **Objective** | Verify counsel can access workflow approvals |
| **Preconditions** | Backend running |
| **Priority** | P1 |

**Steps:**

- [ ] 1. Execute: `curl -s -H "X-Persona: in_house_counsel" http://localhost:8050/workflows/approvals`
- [ ] 2. Verify response is HTTP 200
- [ ] 3. Execute: `curl -s -w "%{http_code}" -H "X-Persona: land_agent" http://localhost:8050/workflows/approvals`
- [ ] 4. Verify response is HTTP 403 Forbidden

**Expected Output:**
- in_house_counsel: 200 OK
- land_agent: 403 Forbidden

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-010: Invalid Persona Rejected

| Field | Value |
|-------|-------|
| **Objective** | Verify invalid persona header is rejected |
| **Preconditions** | Backend running |
| **Priority** | P1 |

**Steps:**

- [ ] 1. Execute: `curl -s -w "%{http_code}" -H "X-Persona: invalid_persona" http://localhost:8050/templates`
- [ ] 2. Verify response is HTTP 401 Unauthorized

**Expected Output:**
- HTTP 401 Unauthorized

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-011: Portal Invite Validation

| Field | Value |
|-------|-------|
| **Objective** | Verify portal invite endpoint validates required payload |
| **Preconditions** | Backend running |
| **Priority** | P1 |

**Steps:**

- [ ] 1. Execute: `curl -s -w "%{http_code}" -X POST -H "X-Persona: landowner" -H "Content-Type: application/json" http://localhost:8050/portal/invites -d '{}'`
- [ ] 2. Verify response is HTTP 422 Unprocessable Entity (validation error)

**Expected Output:**
- HTTP 422 with validation error details

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

### UAT-012: API Root Endpoint

| Field | Value |
|-------|-------|
| **Objective** | Verify API root returns app info |
| **Preconditions** | Backend running |
| **Priority** | P1 |

**Steps:**

- [ ] 1. Execute: `curl -s http://localhost:8050/`
- [ ] 2. Verify response contains `app` and `environment` fields

**Expected Output:**
- HTTP 200
- Response: `{"app": "LandRight", "environment": "dev"}` or similar

| Result | Notes |
|--------|-------|
| ☐ PASS / ☐ FAIL | |

---

## Test Execution Summary

| Priority | Total | Passed | Failed | Skipped |
|----------|-------|--------|--------|---------|
| P0 | 6 | | | |
| P1 | 6 | | | |
| **Total** | **12** | | | |

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| QA Lead | | | |
| Product Owner | | | |
| Engineering Lead | | | |

### Notes & Issues

_Record any issues, observations, or follow-up items below:_

1. 
2. 
3. 

---

## Appendix: Automated Test Coverage Alignment

The manual test cases above align with the automated regression tests in `backend/tests/`:

| UAT ID | Automated Test | File |
|--------|----------------|------|
| UAT-002 | `test_endpoints_rbac[/templates-GET-in_house_counsel-200]` | test_endpoints_rbac.py |
| UAT-002 | `test_endpoints_rbac[/templates-GET-outside_counsel-403]` | test_endpoints_rbac.py |
| UAT-003 | `test_endpoints_rbac[/workflows/binder/export-POST-*]` | test_endpoints_rbac.py |
| UAT-004 | `test_endpoints_rbac[/portal/decision/options-GET-*]` | test_endpoints_rbac.py |
| UAT-005 | `test_endpoints_rbac[/communications-GET-*]` | test_endpoints_rbac.py |
| UAT-006 | `test_rules_engine_fires_for_high_value` | test_rules_engine.py |
| UAT-010 | `test_invalid_persona_header_rejected` | test_endpoints_rbac.py |
| UAT-011 | `test_portal_invite_requires_payload` | test_endpoints_rbac.py |

Run automated tests before manual UAT:
```bash
cd backend && python -m scripts.run_regression
```

---

## Appendix: Playwright E2E Regression Suite

Automated browser-based regression tests are located in `frontend/tests/e2e/`. These tests capture screenshots at each step and save them to `artifacts/e2e/`.

### Running E2E Tests

```bash
# Install Playwright browsers (first time only)
cd frontend && npx playwright install

# Run all E2E tests (headless)
npm run test:e2e

# Run with browser visible
npm run test:e2e:headed

# Run specific test file
npx playwright test tests/e2e/landowner.spec.ts
```

### Screenshot Artifacts

Screenshots are automatically captured:
- **On failure**: Full page screenshot saved to `artifacts/e2e/`
- **Per step**: Explicit `page.screenshot()` calls in tests save to `artifacts/e2e/{test-name}-{step}.png`
- **Traces**: Debug traces saved to `artifacts/e2e/traces/` when `--trace on` is used

### E2E Test Coverage

| Test File | Journey | Steps |
|-----------|---------|-------|
| `landowner.spec.ts` | Landowner portal | Verify invite, view options, submit decision, upload file |
| `agent.spec.ts` | Agent workbench | List parcels, view comms, check packet, upload title |
| `counsel.spec.ts` | Counsel controls | View templates, export binder, check budget |

### CI Integration

The Playwright tests integrate with CI via:

```yaml
# .github/workflows/ci.yml
- name: E2E Tests
  run: |
    cd frontend
    npm ci
    npx playwright install --with-deps chromium
    npm run test:e2e
  env:
    VITE_API_BASE: http://localhost:8050
```

Artifacts are uploaded on failure for debugging.
