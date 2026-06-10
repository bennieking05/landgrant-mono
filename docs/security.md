# Security Model

LandGrant uses **backend-issued JWTs** for API authentication, **persona-based RBAC** for coarse authorization, and **parcel access grants** for row-level scoping of landowner and outside counsel traffic.

## Authentication

- **Login**: `POST /auth/login` with JSON `{ "email", "password" }` returns `{ "access_token", "token_type": "bearer" }`. Passwords are verified with **bcrypt** (`passlib`) against `users.password_hash`.
- **Session introspection**: `GET /auth/me` requires `Authorization: Bearer <JWT>` and returns `sub`, `email`, `firm_id`, `persona`, `roles`, and `permissions` claims (roles/permissions may be extended for SSO).
- **Default deny**: `AuthEnforcementMiddleware` rejects requests without a valid Bearer token except:
  - `GET /healthz`, `GET /health/live`, `GET /readyz`
  - `POST /auth/login`
  - `POST /portal/verify`, `POST /portal/verify/refresh`, `POST /portal/logout`
  - `POST /integrations/dockets` (external webhook; HMAC enforced outside dev)
  - In **dev** only: `GET /docs`, `GET /openapi.json`, `GET /redoc`
- **Malformed / expired tokens** → `401 Unauthorized`.
- **Landowner portal exchange**: Magic-link `POST /portal/verify` creates a **parcel access grant** for the invitee email and returns an **`access_token`** JWT (`persona=landowner`, `sub=portal:<session_id>`) alongside the HttpOnly session cookie.

## JWT claims

| Claim | Purpose |
|-------|---------|
| `sub` | Stable user id (`users.id` for staff; `portal:<session>` for portal JWTs) |
| `email` | Email for grant matching (landowners / counsel) |
| `firm_id` | Tenant scope (nullable for platform-wide reads where allowed) |
| `persona` | Primary RBAC persona (`platform_admin`, `land_agent`, …) |
| `roles` / `permissions` | Optional arrays for future SSO / fine-grained entitlements |

Legacy tokens with `persona=admin` are normalized server-side to **`platform_admin`**.

## Authorization (RBAC)

- Matrix: `backend/app/security/rbac.py` (`PERMISSION_MATRIX`).
- **403 Forbidden** when the persona lacks `(resource, action)`.
- **`platform_admin`**: cross-tenant `/admin` + `admin_platform` reads (replaces generic `admin` for platform operations).
- **`firm_admin`**: firm-scoped admin surfaces only.
- **`X-Persona` is not an authentication mechanism** — the React app and tests must send **Bearer JWTs** only.

## Row-level parcel scope

- Table: `parcel_access_grants` (`parcel_id`, `grantee_email`, `user_id`, `scope_persona`).
- Helpers: `backend/app/security/access_scope.py` — `granted_parcel_ids`, `require_parcel_scope`, `filter_parcels_query`.
- **Landowners** and **outside counsel** only see parcels with matching grants; explicit access to another parcel id → **`403`** (`parcel_access_denied`), not empty lists.
- Internal personas (agents, in-house counsel, firm admin, platform admin) are not grant-filtered at this layer (firm tenancy still applies via `scope_to_firm` / `firm_id`).

## Health checks

- **Public**: `GET /healthz` → `{"status":"ok"}` (liveness).
- **Authenticated**: `GET /health/invite` and `GET /health/esign` require a JWT and `ops` or `admin_platform` read as appropriate.

## Frontend

- JWT stored in **`sessionStorage`** (`landgrant.jwt`); all `api.ts` calls attach `Authorization` when present.
- **Route guards**: `PersonaRoute` + `personaNavMap` — `/admin` requires **`platform_admin`**.
- **Chrome split**: Landowner shell hides internal project/parcel selectors and workbench/counsel/ops/admin nav; internal users do not use landowner-only navigation.

## Tests

- `backend/tests/test_auth_http.py` — anonymous default-deny sweep over registered routes.
- `backend/tests/jwt_helpers.py` — `issue_test_token` / `auth_headers` for pytest.
- `frontend/src/constants/personaNav.test.ts` — navigation invariants.

## SSO / MFA migration

- OIDC/OAuth2 providers can populate the same JWT claims (`sub`, `email`, `firm_id`, `persona`, `roles`, `permissions`) via an IdP bridge; password login remains for staff bootstrap and break-glass until SSO is cut over.
- MFA should be enforced at the IdP; API trusts signed tokens from the issuer configured via `jwt_issuer`, `jwt_audience`, and `jwt_secret` (or asymmetric keys in a future ADR).
