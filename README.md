# LandRight Platform

LandRight is an attorney-in-the-loop platform that ingests landowner cases, orchestrates deterministic rules for every U.S. jurisdiction, and prepares AI-assisted filings with rigorous evidence tracking.

This repository is a mono-repo that contains:

| Directory | Description |
|-----------|-------------|
| `frontend/` | Vite + React portal for landowners, agents, and counsel. |
| `backend/` | FastAPI service, Celery workers, RBAC, deterministic rules engine, and integrations. |
| `infra/` | Terraform IaC for GCP (GKE, Cloud SQL, Pub/Sub, Secret Manager, monitoring). |
| `rules/` | Versioned YAML rule packs for each jurisdiction with citations. |
| `templates/` | Markdown/DOCX templates plus JSON schema metadata. |
| `docs/` | Architecture notes, RBAC matrix, data model, governance, ops, compliance, and pilot plans. |

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Terraform 1.6+
- Docker / container runtime
- `gcloud` CLI for authenticating to GCP

### One-command setup (fresh clone)
From the repository root, run:

```bash
./scripts/setup.sh
```

This script will:
- Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env` if they do not exist
- Start Postgres and Redis via `docker compose up -d` (ports 55432 and 56379)
- Create a Python virtualenv in `backend/` and install dependencies from `backend/requirements-dev.txt`
- Install frontend dependencies with `npm install` in `frontend/`
- Configure git to use the repo’s hooks (`.githooks/`); you can also run `./scripts/install-githooks.sh` manually

After setup, start the backend and frontend as described below.

### Backend
```bash
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
uvicorn app.main:app --reload --port 8050
```
Ensure Postgres and Redis are running (e.g. `docker compose up -d`). Postgres is on port `55432`, Redis on `56379`. See `docs/local-testing.md`.

### Frontend (Vite)
```bash
cd frontend
npm install
npm run dev
```

### Rules + Templates
- Jurisdictional YAML lives in `rules/<state-code>.yaml`. Update version + changelog entries when adjusting logic.
- Document templates live in `templates/library/` with metadata JSON describing variables, locale strings, and privilege classifications.

### Testing
```bash
cd backend
pytest
```
Playwright tests for the portal live under `frontend/tests/` (see instructions in that folder).

### Deployment
- Terraform creates the base infra (GKE, Cloud SQL, Redis, Pub/Sub, Artifact Registry, Secret Manager, Cloud Storage, monitoring).
- GitHub Actions builds and pushes containers, then uses Workload Identity to deploy to GKE.

For full context, review `docs/architecture.md`, `docs/rbac.md`, and `docs/data-model.md`.

### Pushing to a new remote
After creating a GitHub (or other) repository, add it and push:

```bash
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```
