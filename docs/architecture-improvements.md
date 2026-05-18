# Architecture Improvements

> Structural and code organization improvements from the March 2026 audit.

## Summary

The backend was tightened for safety and consistency. The frontend was restructured for persona-awareness and component reuse.

---

## Backend Changes

### 1. RBAC System Completeness

**Action Enum**: Added `CREATE`, `UPDATE`, `DELETE` to match all route usage patterns. The original enum only had `READ`, `WRITE`, `APPROVE`, `EXECUTE`.

**Permission Matrix**: Added 8 new resources across all personas:
- `rules`, `qa`, `approvals`, `task` -- for existing route modules that were missing RBAC entries
- `rag`, `copilot`, `analytics`, `predictions` -- for newly-protected AI/ML routes

### 2. Authentication Architecture (`deps.py`)

Introduced a layered auth pattern:
- **Dev mode**: `X-Persona` header is trusted directly (existing behavior)
- **Non-dev**: Requires `Authorization: Bearer <token>` that is validated before `X-Persona` is accepted

This preserves developer experience while hardening production.

### 3. Middleware Stack (`main.py`)

Added `SecurityHeadersMiddleware` before CORS middleware. Middleware order:
1. SecurityHeaders (adds defense headers)
2. CORS (handles preflight)
3. Route handlers

Swagger UI (`/docs`) is disabled in non-dev environments.

### 4. Webhook Security (`deps.py`, `integrations.py`)

Added `verify_webhook_signature()` utility using HMAC-SHA256. Webhook endpoints use it in non-dev mode to reject unsigned requests.

### 5. Binder Export Scoping (`workflows.py`)

Document queries in binder export now filter by `project_id` from document metadata, preventing cross-project data leakage.

---

## Frontend Changes

### 1. Persona State Management

`AppContext` now includes `persona: Persona` and `setPersona`. This drives:
- Nav item filtering in AppLayout
- Component conditional rendering
- API header injection (via existing `X-Persona` pattern)

### 2. Consistent API Base URL

Standardized all components to use `VITE_API_BASE` instead of mixed `VITE_API_URL` / `VITE_API_BASE`.

### 3. API Type Alignment

Added missing optional fields to TypeScript API types to match the backend response schemas:
- `LitigationCaseItem`: `filing_date`, `service_date`
- `LitigationCaseUpdatePayload`: `status_notes`, `filing_date`, `service_date`
- `CounterOfferPayload`: `counter_amount`, `counter_terms`
- `PaymentLedgerResponse`: `payment_status`, `amount_paid`, `payment_date`
- `OfferItem`: `created_at`, `counter_amount`, `counter_date`
- `CurativeAnalyticsResponse`: `overdue`, `by_status`
- `CurativeItem`: `created_at`
- `AIDecisionDetail`: `reviewed`

---

## Remaining Structural Work

- Consolidate `rules.py` and `rules_ops.py` (both serve `/rules` prefix)
- Consolidate `summaries.py` into rules_ops (shared `/rules/summary` prefix)
- Move hard-coded `DEMO_PROJECTS` in AppContext to API-driven
- Add Alembic migration setup (currently using `create_all` on startup)
- Add proper service layer for routes that query DB directly
- Add frontend route guards (not just nav filtering)
