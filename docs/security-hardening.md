# Security Hardening

> Changes implemented during the March 2026 platform audit.

## Summary

The platform had critical security gaps: unauthenticated routes, untrusted persona headers, wildcard CORS, and missing security response headers. All have been addressed.

---

## Changes Made

### 1. API Key Authentication Layer (`deps.py`)

**Problem**: `X-Persona` header was the sole auth gate. Any client could claim any persona.

**Fix**: Added `_validate_api_key()` that requires a `Bearer` token in non-dev environments. In dev mode, `X-Persona` continues to work without a token for DX. In production, the `Authorization: Bearer <token>` header is required alongside `X-Persona`.

**Impact**: External attackers can no longer impersonate personas in production.

### 2. Protected Previously-Open Routes

**Problem**: `/rag/*`, `/copilot/*`, `/analytics/*`, `/predictions/*` had no auth.

**Fix**: Added `get_current_persona` + `authorize()` calls to all endpoints in these four modules. Health check endpoints remain unauthenticated for monitoring.

**New RBAC resources**: `rag`, `copilot`, `analytics`, `predictions` added to the permission matrix for counsel and admin personas.

### 3. CORS Restriction (`config.py`)

**Problem**: `allowed_origins` defaulted to `["*"]`, allowing any origin.

**Fix**: Default is now `["http://localhost:3050", "https://app.landgrantiq.com", "https://landgrantiq.com"]`. Configurable via `ALLOWED_ORIGINS` env var.

### 4. Security Response Headers (`main.py`)

**Added middleware** that sets on every response:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=63072000; includeSubDomains` (non-dev only)

### 5. Swagger UI Disabled in Production

`docs_url` is only set in dev environment. Production API does not expose `/docs`.

### 6. Webhook Signature Verification (`integrations.py`)

**Problem**: `/integrations/dockets` accepted any request without verifying origin.

**Fix**: Added `verify_webhook_signature()` helper using HMAC-SHA256. In non-dev environments, requests without a valid signature are rejected with 401.

### 7. Binder Export Data Scoping (`workflows.py`)

**Problem**: Binder export queried ALL documents in the database, leaking cross-project data.

**Fix**: Documents query now filters by `project_id` (and optionally `parcel_id`) from the document's `metadata_json`.

### 8. Action Enum Completeness (`rbac.py`)

**Problem**: `Action.UPDATE`, `Action.CREATE`, `Action.DELETE` were used in routes but missing from the enum, causing runtime crashes.

**Fix**: Added `CREATE`, `UPDATE`, `DELETE` to the `Action` enum.

---

## Test Coverage

40 new security tests in `tests/test_security_hardening.py`:
- Security header presence
- Action enum completeness
- Previously-open routes now require persona header
- RBAC matrix completeness for new resources
- Webhook acceptance in dev mode
- Health endpoints remain open

---

## Remaining Risks

- Token auth uses a shared secret (JWT_SECRET). Recommend migrating to proper JWT with RS256 or integrating with an identity provider.
- WebSocket `user_id` is still client-supplied. Should validate against session token once SSO is wired.
- Portal cookies use `SameSite=Lax` -- consider `Strict` for tighter CSRF protection.
- No rate limiting on API endpoints. Recommend adding `slowapi` or Cloud Run concurrency limits.
- Row-level security is application-enforced, not database-enforced. Consider PostgreSQL RLS policies.
