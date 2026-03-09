# Local Testing Guide

1. Start infra dependencies (maps Postgres→55432, Redis→56379):
   ```bash
   docker compose up -d db redis
   ```
2. Copy `.env.example` to `.env` inside `backend/` and adjust if needed.
3. Install deps & run API:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements-dev.txt
   cd backend
   uvicorn app.main:app --reload --port 8050
   ```
4. Seed stub data:
   ```bash
   source .venv/bin/activate
   cd backend
   DATABASE_URL=postgresql+psycopg://landright:landright@localhost:55432/landright python -m scripts.seed_data
   ```
5. Hit health endpoints:
   ```bash
   curl -H "X-Persona: land_agent" http://localhost:8050/cases/PARCEL-001
   ```
6. Frontend (Vite): `cd frontend && npm install && npm run dev` (runs on `http://localhost:3050`).
