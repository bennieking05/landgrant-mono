# Manual regression script (LandGrant)

Use this document before releases or when validating that the stack is **functional end-to-end**. It combines **automated smoke** (optional), **API checks** with `curl`, **UI walkthroughs** by persona, and **rules-engine verification** via tests (not HTTP).

For a full **feature map**, see [`application-functionality-map.md`](./application-functionality-map.md).

---

## 1. Preconditions

| Item | Expected |
|------|----------|
| API | `http://localhost:8050` (or set `API_BASE`) |
| UI | `http://localhost:3050` |
| Database | Dev: SQLite/Postgres per `backend/.env`; API bootstraps demo data in `dev` when `PRJ-001` is missing (`backend/app/main.py`) |

**Start services** (from repo root):

```bash
# Terminal 1: API
cd backend && uvicorn app.main:app --reload --port 8050

# Terminal 2: Frontend
cd frontend && npm run dev
```

**Optional one-shot smoke** (executable script):

```bash
chmod +x scripts/manual-regression-smoke.sh
API_BASE=http://localhost:8050 ./scripts/manual-regression-smoke.sh
```

**Automated tests** (run before or after manual passes):

```bash
cd backend && pytest
cd frontend && npm run test:e2e   # if Playwright is configured
```

---

## 2. Smoke checklist (must pass)

Record **Pass / Fail** and paste any error bodies for failures.

### 2.1 Health and root

| Step | Command | Expect |
|------|---------|--------|
| S1 | `curl -s "$API_BASE/health/live"` | HTTP 200; body contains healthy status |
| S2 | `curl -s "$API_BASE/health/invite"` | HTTP 200 |
| S3 | `curl -s "$API_BASE/health/esign"` | HTTP 200 |
| S4 | `curl -s "$API_BASE/"` | HTTP 200; JSON includes app name and environment |

### 2.2 RBAC spot checks (aligned with `backend/tests/test_endpoints_rbac.py`)

Use `-H "X-Persona: <persona>"` on each request.

| Step | Persona | Method | Path | Expect |
|------|---------|--------|------|--------|
| R1 | `in_house_counsel` | GET | `/templates` | 200 |
| R2 | `outside_counsel` | GET | `/templates` | 403 |
| R3 | `in_house_counsel` | GET | `/workflows/approvals` | 200 |
| R4 | `land_agent` | GET | `/workflows/approvals` | 403 |
| R5 | `land_agent` | GET | `/communications?parcel_id=PARCEL-001` | 200 |
| R6 | `landowner` | GET | `/communications?parcel_id=PARCEL-001` | 403 |
| R7 | `landowner` | GET | `/portal/decision/options` | 200 |
| R8 | `land_agent` | GET | `/portal/decision/options` | 200 (agents have portal read) |
| R9 | `landowner` | GET | `/rag/health` | 403 |
| R10 | `in_house_counsel` | GET | `/rag/health` | 200 |
| R11 | `land_agent` | GET | `/rules/results?parcel_id=PARCEL-001` | 200 |
| R12 | `invalid` | GET | `/templates` | 401 (invalid persona) |

**Example:**

```bash
API_BASE=http://localhost:8050
curl -s -o /dev/null -w "%{http_code}" -H "X-Persona: in_house_counsel" "$API_BASE/templates"
```

### 2.3 Binder export (counsel)

- **POST** `/workflows/binder/export` with JSON `{"project_id":"PRJ-001"}` and `X-Persona: in_house_counsel`.
- **Expect**: In a healthy dev DB, **200** with `bundle_id` is ideal. The automated pytest suite currently expects **500** in its test harness; if you see 500, capture the response `detail` and treat as a regression to fix.

### 2.4 Portal validation

| Step | Command | Expect |
|------|---------|--------|
| P1 | `curl -s -o /dev/null -w "%{http_code}" -X POST -H "X-Persona: landowner" -H "Content-Type: application/json" "$API_BASE/portal/invites" -d '{}'` | 422 |

---

## 3. Rules engine (manual)

There is **no** stable `POST /rules/evaluate` in the public API. Use one of:

**A. Unit test (recommended)**

```bash
cd backend && pytest tests/test_rules_engine.py -v
```

**B. Python REPL** (with project dependencies installed)

```python
from app.services.rules_engine import evaluate_rules
payload = {
    "parcel.assessed_value": 300000,
    "case.dispute_level": "HIGH",
    "appraisal.summary": "",
    "comms.last_contact_at": "2025-01-01T00:00:00Z",
}
results = evaluate_rules("tx", payload)
assert any(r.fired for r in results)
```

**C. Parcel rule history over HTTP**

```bash
curl -s -H "X-Persona: land_agent" "$API_BASE/rules/results?parcel_id=PARCEL-001"
```

Expect JSON with `items` and rule metadata for seeded parcels.

---

## 4. UI manual regression (by persona)

For each persona, open `http://localhost:3050`, select the persona in the header, and walk through the **allowed** nav items (see `frontend/src/constants/personaNav.ts`).

### 4.1 Landowner

- [ ] Home shows portal / intake card.
- [ ] `/intake` loads without blank screen or stuck spinner.
- [ ] Exercise invite/verify/decision/upload flows if present in UI (no console errors).

### 4.2 Land agent

- [ ] `/workbench`: switch tabs **Parcels & packet**, **Title · Appraisal · ROE · Offers**, **Tasks**; confirm panels load (map may lazy-load).
- [ ] Open **AI Copilot** drawer; confirm no hard crash.
- [ ] `/ops`: operational views load.

### 4.3 In-house counsel

- [ ] `/workbench` and `/counsel` both reachable.
- [ ] Counsel tabs: **Approvals & templates**, **Binder & deadlines**, **Litigation**, **Tasks**.
- [ ] Template viewer and binder/deadline sections render.

### 4.4 Outside counsel

- [ ] `/counsel` only (plus home) per nav map; no redirect loop; pages render.

### 4.5 Firm admin

- [ ] `/firm-admin` loads.

### 4.6 Admin

- [ ] All nav destinations open; restricted routes should redirect with message when impersonating stricter personas—verify `PersonaRoute` behavior.

---

## 5. Sign-off (release)

| Area | Tester | Pass? | Notes |
|------|--------|-------|-------|
| Smoke (§2) | | | |
| Rules (§3) | | | |
| UI (§4) | | | |
| Automated pytest / e2e | | | |

---

## 6. Known drift from older docs

- `docs/uat_regression.md` **UAT-004** assumed land agents cannot call `/portal/decision/options`. Current RBAC allows **portal read** for `land_agent`—use **R8** above.
- **UAT-006** referenced `/rules/evaluate`; use **§3** instead.
