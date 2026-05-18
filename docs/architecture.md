# Architecture Overview

This document describes the *current* LandGrant runtime. The earlier draft of
this file referenced a Next.js / GKE / Pub/Sub plan that no longer matches the
code in `frontend/`, `backend/`, and `infra/gcp/`. See
[docs/adr/0004-gcp-cloud-run.md](./adr/0004-gcp-cloud-run.md) for the
deployment decision and [docs/adr/0002-postgresql-postgis.md](./adr/0002-postgresql-postgis.md)
for the database choice.

## High-level shape

- **Personas.** Landowner, land agent, in-house counsel, outside counsel,
  firm admin, and platform admin interact through a single React SPA. Each
  persona is gated by client-side `PersonaRoute` plus backend RBAC (see
  `backend/app/security/rbac.py`).
- **Frontend.** Vite + React 19 single-page app served from Google Cloud
  Storage behind a global HTTPS load balancer (Terraform: `frontend.tf`).
  There is no Next.js / SSR layer — everything is client-rendered and talks
  to the API via `frontend/src/lib/api.ts`.
- **API.** FastAPI on Cloud Run (`backend/app/main.py`) running
  SQLAlchemy 2.0 + Alembic, exposing REST + webhook + SSE endpoints. A
  second Cloud Run service (`landgrant-worker`) hosts Celery consumers for
  async work; both share the same container contract but use different
  entrypoints (`backend/Dockerfile` vs `backend/Dockerfile.worker`).
- **Data.** Cloud SQL Postgres 16 (with PostGIS) is the system of record.
  Redis Memorystore is the Celery broker/result backend and cache.
  ChromaDB (self-hosted in dev, replaceable in prod) backs the RAG index.
  Cloud Storage holds evidence/binders; hashes are mirrored in
  `document_hashes` on Postgres so binders stay tamper-evident.
- **Rules + agents.** Jurisdiction rule packs live in `rules/` as versioned
  YAML. The deterministic rules engine (`backend/app/services/rules_engine.py`)
  emits structured `RuleResult` rows; AI agents (`backend/app/agents/`) only
  *advise*, never decide — every agent output flows through
  `AIDecision` + optional `Escalation` rows and an attorney sign-off gate.

## Key technology choices

- **Frontend.** Vite 6, React 19, TypeScript 5.4, TailwindCSS 3.4,
  react-router-dom 7, Mapbox GL 3. Persona persists via `localStorage`
  (`landgrant.persona`), and `?projectId=…&parcelId=…` query params
  deep-link into the workbench.
- **Backend.** FastAPI 0.115, Pydantic v2, SQLAlchemy 2.0, Alembic 1.13,
  Celery 5.3 (Redis broker), `python-jose` for JWT (HS256 in dev, RS256 via
  Cloud KMS planned). Rate-limiting via `slowapi` keyed on client IP +
  persona.
- **Database.** Postgres 16 + PostGIS 3.4. Migrations in
  `backend/migrations/`. Firm-level multi-tenancy is enforced via a
  `firm_id` column on user-visible rows and the `scope_to_firm` helper in
  `app/security/tenancy.py` (see ADR 0003).
- **Infra.** Terraform (`infra/gcp/`) provisions Cloud Run, Cloud SQL,
  Memorystore, GCS, Secret Manager, Artifact Registry, Cloud Monitoring,
  and a global HTTPS load balancer. `cloudbuild.yaml` at the repo root is
  the CI deploy pipeline; `.github/workflows/ci.yml` runs the test gate.
- **Security.** Bearer JWT required outside `dev`. Security-headers +
  CORS middleware in `app/main.py`. Webhooks verify HMAC via
  `verify_webhook_signature`. Row-level tenant scoping via
  `scope_to_firm` (strict in non-dev; see `app/security/tenancy.py`).
  Secret data lives in Secret Manager; `populate-secrets.sh` wires real
  values after `terraform apply`.

## Environments

| Env | Use | Notes |
|-----|-----|-------|
| `dev` | Local + seeded demo data | `docker-compose up` spins up API :8050, DB :55432, Redis :56379, ChromaDB. Persona can be set via `X-Persona` header; JWT is optional. |
| `staging` | Integration rehearsal | Mirrors prod settings with anonymised data. OTLP export enabled. |
| `prod` | Customer-facing | JWT required; CORS allowlist pinned to `app_domain` / `apex_domain`; rate limiter fails loud; `validate_prod_secrets` aborts startup on missing keys. |

## Deployment flow

1. PR opens → GitHub Actions runs `backend` pytest suite + `frontend`
   `tsc --noEmit`, `eslint`, `vite build`, and Playwright smoke.
2. Merge to `main` → Cloud Build (`cloudbuild.yaml`) builds
   `landgrant-api`, `landgrant-worker`, `landgrant-marketing` images,
   pushes them to Artifact Registry, and redeploys each Cloud Run
   service with the new `$COMMIT_SHA` tag.
3. Frontend: `npm run build` output is synced to the GCS bucket; the
   load balancer serves it with long-cache headers for `assets/**` and
   no-cache for `index.html`.
4. Database migrations run on API container startup when `ALEMBIC_AUTO=1`
   (default in dev/staging); production runs them via an explicit
   `alembic upgrade head` job.

## Observability

- **Traces.** OpenTelemetry OTLP export is opt-in (`ENABLE_OTLP=true`) so
  local dev doesn't spam connection errors when no collector is running.
  In staging/prod, the collector lives next to Cloud Run via the Cloud
  Trace/Cloud Monitoring integration.
- **Logs.** Structured JSON logs via Python's stdlib; Cloud Run's
  built-in log shipping to Cloud Logging.
- **Metrics + alerts.** Cloud Monitoring dashboard defined in
  `infra/gcp/dashboards/service.json`; uptime checks and SLO alerts are
  provisioned by Terraform.
- **Synthetic probes.** Cloud Scheduler hits `/health/live`,
  `/health/invite`, `/health/esign` every minute; the OpsPage in the SPA
  visualises the same probes for on-call humans.

## Known drift vs. this doc

When you change anything structural here, update `docs/data-model.md`,
`docs/adr/0004-gcp-cloud-run.md`, and `docs/testing-strategy.md` in the
same PR so the three views of the system (runtime, decisions, proofs)
don't drift again.
