# LandRight Documentation

> Attorney-in-the-loop eminent domain platform

---

## Quick Links

| Document | Description |
|----------|-------------|
| [M1: Technical Design](./m1-technical-design.md) | Architecture diagrams, ERD, API structure |
| [Dev Environment Setup](./dev-environment-setup.md) | Local development setup guide |
| [API Reference](./api-reference.md) | Detailed API endpoint documentation |
| [Production Deployment](./production-deployment.md) | Deployment guide for GCP |

---

## Documentation Structure

### Architecture & Design

| Document | Description |
|----------|-------------|
| [m1-technical-design.md](./m1-technical-design.md) | **Milestone 1 deliverable** - Complete technical design with diagrams |
| [architecture.md](./architecture.md) | System architecture overview |
| [data-model.md](./data-model.md) | Database entity descriptions |
| [rbac.md](./rbac.md) | Role-based access control matrix |
| [rules-engine.md](./rules-engine.md) | Jurisdiction rules engine specification |

### API Documentation

| Document | Description |
|----------|-------------|
| [api.md](./api.md) | API endpoint summary |
| [api-reference.md](./api-reference.md) | Detailed API reference with examples |

### Architecture Decision Records (ADRs)

| ADR | Title | Status |
|-----|-------|--------|
| [0001](./adr/0001-modern-stack.md) | FastAPI + React Stack | Accepted |
| [0002](./adr/0002-postgresql-postgis.md) | PostgreSQL 16 with PostGIS | Accepted |
| [0003](./adr/0003-rbac-persona-model.md) | RBAC with Persona Model | Accepted |
| [0004](./adr/0004-gcp-cloud-run.md) | GCP Cloud Run Infrastructure | Accepted |

### User Experience

| Document | Description |
|----------|-------------|
| [user-journeys.md](./user-journeys.md) | User journey flows with acceptance criteria |
| [workflows.md](./workflows.md) | Workflow definitions |
| [attorney-workbench.md](./attorney-workbench.md) | Attorney workbench features |

### Operations & Infrastructure

| Document | Description |
|----------|-------------|
| [dev-environment-setup.md](./dev-environment-setup.md) | Local development setup |
| [production-deployment.md](./production-deployment.md) | Production deployment guide |
| [ops.md](./ops.md) | Operations overview |
| [observability.md](./observability.md) | Monitoring and logging |
| [security.md](./security.md) | Security controls |

### Runbooks

| Runbook | Description |
|---------|-------------|
| [runbooks/deploy.md](./runbooks/deploy.md) | Deployment procedures |
| [runbooks/rollback.md](./runbooks/rollback.md) | Rollback procedures |
| [runbooks/incident.md](./runbooks/incident.md) | Incident response |
| [runbooks/backup.md](./runbooks/backup.md) | Backup and restore |

### Testing

| Document | Description |
|----------|-------------|
| [test-strategy.md](./test-strategy.md) | Testing approach |
| [qa-checklist.md](./qa-checklist.md) | QA checklist |
| [local-testing.md](./local-testing.md) | Local testing guide |

### Product & Features

| Document | Description |
|----------|-------------|
| [live-features.md](./live-features.md) | Feature status tracking |
| [missing-items.md](./missing-items.md) | Gap analysis |
| [pilot-plan.md](./pilot-plan.md) | Pilot program plan |

### Jurisdiction Rules

| Document | Description |
|----------|-------------|
| [state-requirements-buckets.md](./state-requirements-buckets.md) | State requirements categories |
| [state-requirements-map.md](./state-requirements-map.md) | State requirements mapping |
| [rules-changelog.md](./rules-changelog.md) | Rules version history |

### AI & Integrations

| Document | Description |
|----------|-------------|
| [ai-pipeline.md](./ai-pipeline.md) | AI pipeline architecture |
| [ai-first-modules.md](./ai-first-modules.md) | AI module specifications |
| [integrations.md](./integrations.md) | External integrations |

---

## Milestone Documentation

### Milestone 1: Technical Design & Product Refinement
**Status:** Complete | **Sprints:** 1-2 | **Release:** March 3, 2026

- [x] [Technical Design Document](./m1-technical-design.md) with diagrams
- [x] [Development Environment Setup](./dev-environment-setup.md)
- [x] [Architecture Decision Records](./adr/)
- [x] [Data Model Documentation](./data-model.md)
- [x] [API Reference](./api-reference.md)

### Milestone 2: Backend MVP API
**Status:** Complete | **Sprints:** 3-4 | **Release:** March 31, 2026

- [x] All MVP API endpoints implemented
- [x] [API Documentation](./api.md)
- [x] Unit test coverage

### Milestone 3: Frontend Internal Web App
**Status:** Complete | **Sprints:** 5-6 | **Release:** April 28, 2026

- [x] Agent workbench
- [x] Counsel controls
- [x] Operations dashboard
- [x] [User Journeys](./user-journeys.md)

### Milestone 4: Landowner Portal & Hardening
**Status:** Complete | **Sprints:** 7-8 | **Release:** May 26, 2026

- [x] Magic link authentication
- [x] E-sign integration
- [x] [Security Documentation](./security.md)

### Milestone 5: UAT & Production-Ready
**Status:** Complete | **Sprints:** 9-10 | **Release:** June 23, 2026

- [x] E2E test coverage
- [x] [Production Deployment Guide](./production-deployment.md)
- [x] [Runbooks](./runbooks/)

---

## Quick Reference

### Local Development Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 3050 | http://localhost:3050 |
| Backend API | 8050 | http://localhost:8050 |
| API Docs | 8050 | http://localhost:8050/docs |
| PostgreSQL | 55432 | `postgresql://landright:landright@localhost:55432/landright` |
| Redis | 56379 | `redis://localhost:56379/0` |

### Key Commands

```bash
# Start infrastructure
docker compose up -d

# Start backend
cd backend && uvicorn app.main:app --reload --port 8050

# Start frontend
cd frontend && npm run dev

# Run backend tests
cd backend && pytest

# Run E2E tests
cd frontend && npx playwright test
```

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/db/models.py` | Database models |
| `backend/app/api/routes/` | API endpoints |
| `backend/app/security/rbac.py` | Permission matrix |
| `frontend/src/App.tsx` | Frontend routes |
| `docker-compose.yml` | Local infrastructure |
| `infra/gcp/` | Terraform configs |

---

*Last updated: February 2026*
