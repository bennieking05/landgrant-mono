# Development Environment Setup

**Milestone 1 Deliverable**

This guide covers setting up the LandRight development environment from scratch.

---

## Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Node.js | 20+ | `brew install node` |
| Python | 3.11+ | `brew install python@3.11` |
| Docker | 24+ | [Docker Desktop](https://docker.com/products/docker-desktop) |
| PostgreSQL Client | 16 | `brew install libpq` |
| Git | 2.40+ | `brew install git` |

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/landright/land-right.git
cd land-right

# 2. Start infrastructure (PostgreSQL + Redis)
docker compose up -d

# 3. Setup backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 4. Run database migrations
alembic upgrade head

# 5. Seed test data (optional)
python -m scripts.seed_data

# 6. Start backend server
uvicorn app.main:app --reload --port 8050

# 7. Setup frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Development Machine                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Frontend   │    │   Backend    │    │   Workers    │  │
│  │  Vite Dev    │───▶│   FastAPI    │───▶│   Celery     │  │
│  │  Port 3050   │    │  Port 8050   │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
│                             ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 Docker Compose                       │   │
│  │  ┌─────────────────┐    ┌─────────────────┐         │   │
│  │  │   PostgreSQL    │    │     Redis       │         │   │
│  │  │   Port 55432    │    │   Port 56379    │         │   │
│  │  └─────────────────┘    └─────────────────┘         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Setup

### 1. Infrastructure Services

```bash
# Start PostgreSQL and Redis
docker compose up -d

# Verify services are running
docker compose ps

# Expected output:
# NAME                SERVICE   STATUS
# land-right-db-1     db        running (healthy)
# land-right-cache-1  cache     running (healthy)

# View logs if needed
docker compose logs -f db
docker compose logs -f cache
```

**Service Ports:**
| Service | Container Port | Host Port | Connection String |
|---------|---------------|-----------|-------------------|
| PostgreSQL | 5432 | 55432 | `postgresql://landright:landright@localhost:55432/landright` |
| Redis | 6379 | 56379 | `redis://localhost:56379/0` |

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools

# Copy environment file
cp .env.example .env

# Edit .env as needed (defaults work for local dev)
```

**Environment Variables (.env):**

```bash
# Application
APP_NAME=landright-api
ENVIRONMENT=dev

# Database
DATABASE_URL=postgresql+psycopg://landright:landright@localhost:55432/landright

# Redis
REDIS_URL=redis://localhost:56379/0

# Storage (local development)
EVIDENCE_BUCKET=local-evidence

# CORS
ALLOWED_ORIGINS=["http://localhost:3050"]

# Optional: AI Services
OPENAI_API_KEY=sk-...        # For AI features
ANTHROPIC_API_KEY=sk-ant-... # Alternative LLM

# Optional: External Services
DOCUSIGN_INTEGRATION_KEY=    # E-signatures
SENDGRID_API_KEY=            # Email
MAPBOX_TOKEN=                # Maps
```

### 3. Database Migrations

```bash
# Run all migrations
alembic upgrade head

# Create new migration (after model changes)
alembic revision --autogenerate -m "Add new_table"

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### 4. Seed Data

```bash
# Seed test data for development
python -m scripts.seed_data

# This creates:
# - Sample projects (Texas, Indiana)
# - Test parcels with geometry
# - Sample parties
# - Document templates
# - Rule packs
```

### 5. Start Backend Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8050

# Or use the run script
./run.sh

# API available at:
# - http://localhost:8050
# - Docs: http://localhost:8050/docs
# - ReDoc: http://localhost:8050/redoc
```

### 6. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env
# VITE_API_URL=http://localhost:8050
# VITE_MAPBOX_TOKEN=pk.xxx  # Get from mapbox.com
```

### 7. Start Frontend

```bash
# Development mode
npm run dev

# Frontend available at:
# - http://localhost:3050
```

---

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_cases.py

# Run with verbose output
pytest -v

# Run async tests
pytest -v tests/test_api/
```

### Frontend Tests

```bash
cd frontend

# Run E2E tests
npx playwright test

# Run with UI
npx playwright test --ui

# Run specific test
npx playwright test tests/e2e/agent.spec.ts

# Update snapshots (visual regression)
npx playwright test --update-snapshots
```

---

## Common Development Tasks

### Adding a New API Endpoint

1. Create/update route in `backend/app/api/routes/`
2. Add Pydantic models for request/response
3. Register route in `backend/app/main.py`
4. Add tests in `backend/tests/test_api/`
5. Update API documentation if needed

### Adding a New Database Model

1. Add model in `backend/app/db/models.py`
2. Create migration: `alembic revision --autogenerate -m "Add model_name"`
3. Run migration: `alembic upgrade head`
4. Add to seed script if needed

### Adding a New Frontend Page

1. Create page in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`
3. Add navigation in `frontend/src/components/AppLayout.tsx`
4. Add E2E tests

---

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker compose ps db

# Check PostgreSQL logs
docker compose logs db

# Connect directly to database
psql postgresql://landright:landright@localhost:55432/landright

# Reset database (destructive!)
docker compose down -v
docker compose up -d
alembic upgrade head
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker compose ps cache

# Test Redis connection
redis-cli -p 56379 ping
# Should return: PONG
```

### Port Conflicts

```bash
# Check what's using a port
lsof -i :8050
lsof -i :3050

# Kill process using port
kill -9 <PID>
```

### Python Virtual Environment

```bash
# Recreate virtual environment
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Node Modules Issues

```bash
# Clear and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

## IDE Configuration

### VS Code Extensions

- Python (Microsoft)
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- GitLens
- Docker

### Recommended Settings

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

---

## Next Steps

After setup, you can:

1. **Explore the API:** http://localhost:8050/docs
2. **View the app:** http://localhost:3050
3. **Run tests:** `pytest` (backend) or `npx playwright test` (frontend)
4. **Read architecture docs:** `docs/architecture.md`

---

*Last updated: February 2026*
