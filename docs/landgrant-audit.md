# LandGrant Platform Audit

> **Date**: March 2026 (historical snapshot)
> **Scope**: Full-stack audit of security, structure, functionality, and UX
> **Status**: **Historical findings log.** Many P0/P1 items listed below have
> since been resolved. See the "Resolution cross-reference" table immediately
> below before treating any finding as current. For live gap tracking, consult
> [`architecture-improvements.md`](./architecture-improvements.md),
> [`security-hardening.md`](./security-hardening.md), and
> [`functional-gap-closure.md`](./functional-gap-closure.md).

## Resolution cross-reference

| Audit finding | Status | Authoritative doc / code |
|---------------|--------|---------------------------|
| `Action.UPDATE/CREATE/DELETE` missing on `Action` enum | Resolved | `backend/app/security/rbac.py` now defines all five actions |
| `user.get("sub")` on ORM object | Resolved | `backend/app/api/routes/admin.py` uses attribute access |
| `X-Persona` header is sole auth gate | Partially resolved | `backend/app/api/deps.py` `_validate_api_key` requires Bearer outside dev; see [security-hardening.md](./security-hardening.md) |
| `/rag/*`, `/copilot/*`, `/analytics/*`, `/predictions/*` unauthenticated | Resolved | All four now call `authorize(...)` — see `backend/tests/test_endpoints_rbac.py` |
| Webhook signature verification | Resolved | `backend/app/api/deps.py` `verify_webhook_signature` + route wiring |
| CORS `*` default | Resolved | `backend/app/core/config.py` `allowed_origins` defaults to known hosts |
| Missing RBAC resources in matrix | Resolved | `PERMISSION_MATRIX` in `backend/app/security/rbac.py` |

The remaining sections below are preserved verbatim for historical context but should NOT be treated as current blockers without cross-checking against the resolved docs.

---

## Architecture Summary

LandGrant is an attorney-in-the-loop eminent domain platform deployed on GCP:

- **Frontend**: Vite + React SPA at `app.landgrantiq.com` (GCS + CDN)
- **Backend**: FastAPI at `api.landgrantiq.com` (Cloud Run, 194 routes)
- **Workers**: Celery on Cloud Run (`landgrant-worker`)
- **Database**: Cloud SQL PostgreSQL 16 with PostGIS
- **Cache**: Memorystore Redis
- **Storage**: GCS for documents, templates, binders
- **AI**: Gemini 1.5 Flash (summarization/drafting only, never decisions)
- **Marketing**: Next.js on Cloud Run at `landgrantiq.com`

Six personas: `landowner`, `land_agent`, `in_house_counsel`, `outside_counsel`, `firm_admin`, `admin`.

---

## P0: Runtime Crashes

### 1. `Action.UPDATE` / `Action.CREATE` / `Action.DELETE` do not exist

The `Action` enum in `backend/app/security/rbac.py` defines only `READ`, `WRITE`, `APPROVE`, `EXECUTE`. However, route files reference `Action.UPDATE` (workflows.py, tasks.py), `Action.CREATE` (tasks.py), and `Action.DELETE` (tasks.py). These will raise `AttributeError` at runtime.

**Files affected**:
- `backend/app/api/routes/workflows.py` (lines 306, 392)
- `backend/app/api/routes/tasks.py` (lines 276, 457, 508, 536, 566, 643, 768, 796)

### 2. `user.get("sub")` on ORM object

Admin routes call `user.get("sub", "unknown")` on the `User` SQLAlchemy model instance returned by `get_current_user`. ORM objects don't have a `.get()` method -- this crashes with `AttributeError`.

**Files affected**:
- `backend/app/api/routes/admin.py` (lines 178, 245, 333)

---

## P0: Security Gaps

### 1. X-Persona header is the only auth gate

`deps.py` `get_current_persona` trusts the `X-Persona` header with no verification. Any HTTP client can send `X-Persona: admin` and gain full platform admin access. `get_current_user` returns a hardcoded stub `User` object.

### 2. Five route groups have NO authentication

The following route modules do not use `get_current_persona` or `authorize()`:
- `/rag/*` (RAG search, ingest, stats)
- `/copilot/*` (conversational AI)
- `/analytics/*` (predictive settlement, risk)
- `/predictions/*` (ML predictions, config)
- Health endpoints within these modules

### 3. Webhook endpoints have no signature verification

- `POST /esign/webhook` -- no Adobe Sign signature check
- `POST /integrations/dockets` -- no Lob/external signature check

### 4. WebSocket accepts client-supplied user_id

`/ws/notifications` accepts `user_id` from the client JSON payload with no server-side verification.

### 5. CORS allows all origins

`config.py` defaults `allowed_origins` to `["*"]`.

---

## P1: Broken Functionality

### 1. RBAC resources missing from PERMISSION_MATRIX

Four resources used in `authorize()` calls are not in the matrix, causing 403 for all personas:
- `rules` (used in `rules_ops.py`, `summaries.py`)
- `qa` (used in `qa.py`)
- `approvals` (used in `approvals_api.py`)
- `task` (used in `tasks.py`)

### 2. Seven orphan frontend components

Built but never imported into any page:
- `ROEPanel`, `LitigationPanel`, `NegotiationPanel`
- `AIDecisionDashboard`, `DocumentExtraction`
- `TaskManager`, `NotificationBell`

### 3. No frontend route guards

All pages (including Admin, Firm Admin) are accessible to any user regardless of persona.

### 4. Binder export data leak

`workflows.py` binder export queries ALL `Document` rows (`db.query(models.Document)...all()`) without filtering by project or parcel.

---

## P1: Structural Issues

### 1. Inconsistent API base URL in frontend

Most components use `VITE_API_BASE` via `lib/api.ts`, but `TaskManager` uses `VITE_API_URL`.

### 2. Duplicate route prefixes

`rules.py` and `rules_ops.py` both use `/rules` prefix. `summaries.py` uses `/rules/summary`.

### 3. Hard-coded demo projects

`AppContext.tsx` has `DEMO_PROJECTS` array instead of loading from API.

---

## Prioritized Remediation Plan

1. Fix runtime crashes (Action enum, admin user.get)
2. Add missing RBAC resources to permission matrix
3. Add auth to unprotected routes
4. Add API key auth layer for non-dev environments
5. Fix CORS defaults and add security headers
6. Wire orphan components into pages
7. Scope binder export to project
8. Add persona-aware frontend routing
9. Improve page layouts and UX
10. Extend test coverage
11. Create documentation and Cursor rules
