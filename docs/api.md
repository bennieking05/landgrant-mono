# API Surface

Full endpoint reference for the LandRight backend API. OpenAPI schema is auto-generated at `/docs`.

## Authentication

All endpoints require the `X-Persona` header to identify the caller's role:

```
X-Persona: landowner | land_agent | in_house_counsel | outside_counsel | admin
```

Invalid or missing persona returns `401 Unauthorized`. Insufficient permissions return `403 Forbidden`.

---

## Health Endpoints

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/health/live` | Liveness probe | Any |
| GET | `/health/invite` | Invite flow synthetic check | Any |
| GET | `/health/esign` | E-sign vendor check | Any |

---

## Cases

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| POST | `/cases` | Intake new parcels with parties | land_agent |
| GET | `/cases/{parcel_id}` | Retrieve parcel snapshot | land_agent, in_house_counsel |

### Request: POST /cases

```json
{
  "project_id": "PRJ-001",
  "parcels": [
    {
      "county_fips": "48439",
      "stage": "intake",
      "risk_score": 0,
      "parties": [{ "name": "Owner Name", "role": "owner", "email": "owner@example.com" }]
    }
  ],
  "jurisdiction_code": "TX",
  "stage": "intake"
}
```

---

## Parcels

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/parcels` | List/filter parcels | land_agent, in_house_counsel |

### Query Parameters

- `project_id` - Filter by project
- `stage` - Filter by stage (intake, negotiation, offer_sent, closed)
- `min_risk` - Minimum risk score
- `deadline_before` - ISO date for upcoming deadlines
- `limit` / `offset` - Pagination

---

## Templates

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/templates` | List approved templates | in_house_counsel |
| POST | `/templates/render` | Render template with variables | in_house_counsel |

### Request: POST /templates/render

```json
{
  "template_id": "fol",
  "locale": "en-US",
  "variables": { "owner_name": "John Doe", "service_date": "2026-01-24" },
  "persist": true,
  "project_id": "PRJ-001",
  "parcel_id": "PARCEL-001"
}
```

---

## AI Drafts

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| POST | `/ai/drafts` | Generate AI-assisted draft (sync) | in_house_counsel |
| POST | `/ai/drafts/async` | Generate AI-assisted draft (async) | in_house_counsel |
| GET | `/ai/health` | Check AI service availability | Any |

### Request: POST /ai/drafts

```json
{
  "jurisdiction": "TX",
  "payload": { "parcel.assessed_value": 300000, "case.dispute_level": "HIGH" },
  "task_type": "draft_analysis"
}
```

---

## Workflows

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| POST | `/workflows/tasks` | Create attorney review task | in_house_counsel |
| GET | `/workflows/approvals` | List pending approvals | in_house_counsel |
| POST | `/workflows/binder/export` | Export audit binder bundle | in_house_counsel |

---

## Portal (Landowner)

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| POST | `/portal/invites` | Send magic-link invite | landowner |
| POST | `/portal/verify` | Verify invite token | landowner |
| GET | `/portal/decision/options` | Get decision choices | landowner |
| POST | `/portal/decision` | Submit decision | landowner |
| GET | `/portal/uploads` | List uploaded files | landowner |
| POST | `/portal/uploads` | Upload supporting document | landowner |

### Request: POST /portal/invites

```json
{
  "email": "owner@example.com",
  "parcel_id": "PARCEL-001",
  "project_id": "PRJ-001"
}
```

### Request: POST /portal/decision

```json
{
  "parcel_id": "PARCEL-001",
  "selection": "Accept",
  "note": "Optional note"
}
```

---

## Communications

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/communications` | List parcel comms log | land_agent, in_house_counsel |

### Query Parameters

- `parcel_id` (required) - Parcel to query

---

## Packet

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/packet/checklist` | Get pre-offer packet status | land_agent |

### Query Parameters

- `parcel_id` (required) - Parcel to check

---

## Rules

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/rules/results` | Get fired rule citations | land_agent, in_house_counsel |

### Query Parameters

- `parcel_id` (required) - Parcel to query

---

## Budgets

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/budgets/summary` | Get project budget utilization | in_house_counsel |

### Query Parameters

- `project_id` (required) - Project to query

---

## Binder

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/binder/status` | Get binder section status | in_house_counsel |

### Query Parameters

- `project_id` (required) - Project to query

---

## Notifications

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| POST | `/notifications/preview` | Preview/send notification | land_agent, in_house_counsel |

### Request: POST /notifications/preview

```json
{
  "template_id": "portal_invite",
  "channel": "email",
  "to": "owner@example.com",
  "project_id": "PRJ-001",
  "parcel_id": "PARCEL-001",
  "variables": {}
}
```

---

## Deadlines

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/deadlines` | List project deadlines | in_house_counsel |
| POST | `/deadlines` | Create manual deadline | in_house_counsel |
| GET | `/deadlines/ical` | Export iCal feed | in_house_counsel |
| POST | `/deadlines/derive` | Derive statutory deadlines | in_house_counsel |

### Request: POST /deadlines/derive

```json
{
  "project_id": "PRJ-001",
  "parcel_id": "PARCEL-001",
  "jurisdiction": "IN",
  "anchor_events": { "offer_served": "2026-01-24" },
  "persist": true,
  "timezone": "America/Indiana/Indianapolis"
}
```

---

## Title

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/title/instruments` | List title chain docs | land_agent |
| POST | `/title/instruments` | Upload deed/survey | land_agent |

---

## Appraisals

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/appraisals` | Get parcel appraisal | land_agent |
| POST | `/appraisals` | Create/update appraisal | land_agent |

### Request: POST /appraisals

```json
{
  "parcel_id": "PARCEL-001",
  "value": 350000,
  "summary": "Commercial property with highway frontage",
  "comps": [{ "address": "123 Main St", "sale_price": 340000, "sale_date": "2025-06-15" }]
}
```

---

## Operations

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/ops/routes/plan` | Generate optimized visit route | land_agent |

### Query Parameters

- `project_id` (required) - Project to plan

---

## Outside Counsel

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| GET | `/outside/repository/completeness` | Check required docs present | outside_counsel |
| POST | `/outside/case/initiate` | Start litigation draft | outside_counsel |
| POST | `/outside/status` | Update case status | outside_counsel |

### Request: POST /outside/case/initiate

```json
{
  "project_id": "PRJ-001",
  "parcel_id": "PARCEL-001",
  "template_id": "condemnation_complaint"
}
```

---

## Integrations

| Method | Path | Description | Persona |
|--------|------|-------------|---------|
| POST | `/integrations/dockets` | Receive docket webhook | External |

---

## Error Responses

| Code | Description |
|------|-------------|
| 401 | Invalid or missing X-Persona header |
| 403 | Persona lacks permission for resource/action |
| 404 | Resource not found |
| 410 | Invite expired |
| 413 | File too large (uploads) |
| 422 | Validation error |
| 429 | Rate limited (too many failed attempts) |

---

## Pagination

List endpoints support:

- `limit` - Max items to return (default 100, max 500)
- `offset` - Items to skip

Response includes `total` count for pagination UI.
