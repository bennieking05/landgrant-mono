# Architecture Overview

This document distills the LandRight-AI dossier, User Journeys swimlane, and EminentAI backlog into an actionable system blueprint.

## High-Level Diagram
- Landowner, Land Agent, Counsel (in-house + outside) interact through the Next.js portal.
- FastAPI backend exposes REST + webhook endpoints and manages deterministic workflows.
- Vertex AI is *not* in the critical path for statutory rules—Gemini is only used for summarization inside the attorney workbench, never for final decisions.
- Evidence, templates, and immutable binders are stored in Cloud Storage (CMEK protected) with hashed manifests recorded in Postgres.
- Pub/Sub fan-outs docket/webhook events into Celery workers running on GKE.
- Deterministic rules engine loads YAML packs per jurisdiction and emits structured `RuleResult` rows with citations + field values that triggered each rule.

## Technology Choices
- **Frontend**: Next.js 15 (App Router, React Server Components), Tailwind, shadcn/ui, ESRI JS API for parcel visualization, Clerk (swapable) for SSO + MFA.
- **Backend**: FastAPI + SQLAlchemy + Pydantic v2, Celery + Redis (MemoryStore) for tasks, httpx for integrations, Auth0/Clerk JWT validation middleware.
- **Database**: Cloud SQL Postgres 16 with row-level security enforcing tenant + persona scopes.
- **Infra**: Terraform-provisioned GKE Autopilot, Pub/Sub, Artifact Registry, Cloud Storage, Secret Manager, Cloud Monitoring, Cloud Build (optional), Sentry / OpenTelemetry exporters.
- **Security**: SOC 2 Day 1 controls (SSO, MFA, change mgmt, DPAs, TLS 1.2+, KMS, privacy banners, attorney sign-off gates, Kovel tagging, law firm segmentation).

## Environments
- `dev`: seeded with 5 projects × 50 parcels × 3 jurisdictions (anonymized) to rehearse flows quickly.
- `staging`: mirrors prod settings, uses masked copies of legal documents.
- `prod`: break-glass workflows, audited access, log retention 7y, litigation hold switch.

## Deployment Flow
1. Developer opens PR.
2. GitHub Actions runs lint/tests (backend + frontend), Terraform validate, and uploads coverage.
3. On merge, CI builds container images, pushes to Artifact Registry, and deploys via `kubectl` to GKE using Workload Identity.
4. Argo Rollouts (future) manages progressive delivery with health checks tied to SLOs (P95 <300 ms, uptime 99.5%).

## Observability
- OpenTelemetry instrumentation covers HTTP, Celery, and DB spans.
- Sentry collects frontend/backoffice errors with persona annotations.
- Prometheus metrics exported to Cloud Monitoring; dashboards + alert policies codified in Terraform.
- Synthetic monitors (invites, e-sign, docket ingestion) run via Cloud Scheduler hitting dedicated endpoints.
