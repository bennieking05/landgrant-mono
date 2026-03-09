# Verification Runbook (Local)

This runbook is the **hands-on checklist** for verifying all backlog functionality locally.
It is designed to be repeatable and to surface which stories are still stubbed vs implemented.

## Prereqs
- Docker
- Python 3.11+
- Node.js 20+

## 1) Start local dependencies

```bash
cd /Users/bennieking/Sites/land-right
docker compose up -d db redis
```

## 2) Start backend API

```bash
cd /Users/bennieking/Sites/land-right
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
uvicorn app.main:app --reload --port 8050
```

Backend base URL: `http://localhost:8050`

## 3) Seed demo data (optional but recommended)

In a second terminal:

```bash
cd /Users/bennieking/Sites/land-right
source .venv/bin/activate
cd backend
DATABASE_URL=postgresql+psycopg://landright:landright@localhost:55432/landright python -m scripts.seed_data
```

## 4) Start frontend

```bash
cd /Users/bennieking/Sites/land-right/frontend
npm install
npm run dev
```

Frontend base URL: `http://localhost:3050`

## 5) API smoke checks (curl)

### Health

```bash
curl -s http://localhost:8050/health/live
curl -s http://localhost:8050/health/invite
curl -s http://localhost:8050/health/esign
```

### Golden path: Agent creates a case and loads parcel

```bash
curl -s -X POST http://localhost:8050/cases \
  -H 'Content-Type: application/json' \
  -H 'X-Persona: land_agent' \
  -d '{
    "project_id": "PRJ-001",
    "jurisdiction_code": "TX",
    "parcels": [{"county_fips": "48439", "stage": "intake", "risk_score": 50, "parties": []}]
  }'
```

Then load a known seeded parcel (or one you created above):

```bash
curl -s http://localhost:8050/cases/PARCEL-001 -H 'X-Persona: land_agent'
```

### Workbench reads: comms log, packet checklist, rule results

```bash
curl -s 'http://localhost:8050/communications?parcel_id=PARCEL-001' -H 'X-Persona: land_agent'
curl -s 'http://localhost:8050/packet/checklist?parcel_id=PARCEL-001' -H 'X-Persona: land_agent'
curl -s 'http://localhost:8050/rules/results?parcel_id=PARCEL-001' -H 'X-Persona: land_agent'
```

### Landowner: invite, upload, decision

Invite (note: currently stubbed; later must create an expiring magic-link + outbox preview payload):

```bash
curl -s -X POST http://localhost:8050/portal/invites \
  -H 'Content-Type: application/json' \
  -H 'X-Persona: landowner' \
  -d '{"email":"owner@example.com","project_id":"PRJ-001","parcel_id":"PARCEL-001"}'
```

Upload a small file (replace path):

```bash
curl -s -X POST http://localhost:8050/portal/uploads \
  -H 'X-Persona: landowner' \
  -F 'parcel_id=PARCEL-001' \
  -F 'file=@/Users/bennieking/Sites/land-right/README.md'
```

List uploads:

```bash
curl -s 'http://localhost:8050/portal/uploads?parcel_id=PARCEL-001' -H 'X-Persona: landowner'
```

Submit decision:

```bash
curl -s -X POST http://localhost:8050/portal/decision \
  -H 'Content-Type: application/json' \
  -H 'X-Persona: landowner' \
  -d '{"parcel_id":"PARCEL-001","selection":"Counter","note":"Need to discuss terms"}'
```

### Counsel: approvals queue, budget, binder status/export

```bash
curl -s http://localhost:8050/workflows/approvals -H 'X-Persona: in_house_counsel'
curl -s 'http://localhost:8050/budgets/summary?project_id=PRJ-001' -H 'X-Persona: in_house_counsel'
curl -s 'http://localhost:8050/binder/status?project_id=PRJ-001' -H 'X-Persona: in_house_counsel'
curl -s -X POST http://localhost:8050/workflows/binder/export -H 'X-Persona: in_house_counsel'
```

## 6) Negative RBAC checks (must return 403)

Landowner cannot read communications:

```bash
curl -i -s 'http://localhost:8050/communications?parcel_id=PARCEL-001' -H 'X-Persona: landowner'
```

Land agent cannot export binder:

```bash
curl -i -s -X POST http://localhost:8050/workflows/binder/export -H 'X-Persona: land_agent'
```

Outside counsel cannot read templates unless explicitly allowed:

```bash
curl -i -s http://localhost:8050/templates -H 'X-Persona: outside_counsel'
```

## 7) UI smoke steps (browser)

1. Open `http://localhost:3050` and navigate to:
   - `/intake` (landowner portal page)
   - `/workbench` (agent workbench)
   - `/counsel` (counsel controls)
2. Confirm each card loads without errors and calls the corresponding API endpoints.
3. Repeat the above after any backend changes to ensure wiring remains intact.

## Endpoint URL Index (Local)

Backend base: `http://localhost:8050`

- **Root**
  - `GET http://localhost:8050/`
- **Health**
  - `GET http://localhost:8050/health/live`
  - `GET http://localhost:8050/health/invite`
  - `GET http://localhost:8050/health/esign`
- **Cases**
  - `POST http://localhost:8050/cases`
  - `GET http://localhost:8050/cases/{parcel_id}`
- **Parcels**
  - `GET http://localhost:8050/parcels?project_id={project_id}&stage={stage}&min_risk={min_risk}&deadline_before={iso}`
- **Templates**
  - `GET http://localhost:8050/templates`
  - `POST http://localhost:8050/templates/render`
- **AI**
  - `POST http://localhost:8050/ai/drafts`
- **Portal**
  - `POST http://localhost:8050/portal/invites`
  - `GET http://localhost:8050/portal/decision/options`
  - `POST http://localhost:8050/portal/decision`
  - `GET http://localhost:8050/portal/uploads?parcel_id={parcel_id}`
  - `POST http://localhost:8050/portal/uploads` (multipart form)
- **Notifications**
  - `POST http://localhost:8050/notifications/preview`
- **Communications**
  - `GET http://localhost:8050/communications?parcel_id={parcel_id}`
- **Packet**
  - `GET http://localhost:8050/packet/checklist?parcel_id={parcel_id}`
- **Rules**
  - `GET http://localhost:8050/rules/results?parcel_id={parcel_id}`
- **Budgets**
  - `GET http://localhost:8050/budgets/summary?project_id={project_id}`
- **Binder**
  - `GET http://localhost:8050/binder/status?project_id={project_id}`
- **Workflows**
  - `POST http://localhost:8050/workflows/tasks`
  - `GET http://localhost:8050/workflows/approvals`
  - `POST http://localhost:8050/workflows/binder/export`
- **Deadlines**
  - `GET http://localhost:8050/deadlines?project_id={project_id}`
  - `POST http://localhost:8050/deadlines`
  - `GET http://localhost:8050/deadlines/ical?project_id={project_id}`
- **Integrations**
  - `POST http://localhost:8050/integrations/dockets`
- **Title**
  - `GET http://localhost:8050/title/instruments?parcel_id={parcel_id}`
  - `POST http://localhost:8050/title/instruments` (multipart form)
- **Appraisals**
  - `GET http://localhost:8050/appraisals?parcel_id={parcel_id}`
  - `POST http://localhost:8050/appraisals`
- **Ops**
  - `GET http://localhost:8050/ops/routes/plan?project_id={project_id}`
- **Outside counsel**
  - `GET http://localhost:8050/outside/repository/completeness?project_id={project_id}`
  - `POST http://localhost:8050/outside/case/initiate`
  - `POST http://localhost:8050/outside/status`

Frontend base: `http://localhost:3050`
- `GET http://localhost:3050/`
- `GET http://localhost:3050/intake`
- `GET http://localhost:3050/workbench`
- `GET http://localhost:3050/counsel`


