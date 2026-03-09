#!/bin/bash

# LandRight one-command bootstrap for a fresh clone
# Copies env templates, starts Postgres/Redis, installs backend and frontend deps, installs git hooks.
#
# Usage: ./scripts/setup.sh
# Run from repository root.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "============================================"
echo "  LandRight setup"
echo "============================================"
echo ""

# 1. Copy .env.example to .env where missing
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env from backend/.env.example"
else
  echo "backend/.env already exists, skipping"
fi
if [ ! -f frontend/.env ]; then
  cp frontend/.env.example frontend/.env
  echo "Created frontend/.env from frontend/.env.example"
else
  echo "frontend/.env already exists, skipping"
fi
echo ""

# 2. Start docker-compose (Postgres + Redis)
echo "Starting Postgres and Redis (docker-compose)..."
docker compose up -d
echo "Waiting for Postgres to be ready..."
sleep 3
echo ""

# 3. Python venv and backend deps
echo "Setting up backend (Python venv + deps)..."
cd "$REPO_ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
. .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements-dev.txt -q
deactivate
cd "$REPO_ROOT"
echo ""

# 4. Frontend npm deps
echo "Installing frontend dependencies..."
cd "$REPO_ROOT/frontend"
npm install
cd "$REPO_ROOT"
echo ""

# 5. Git hooks
if [ -d .githooks ]; then
  echo "Installing git hooks..."
  chmod +x .githooks/*
  git config core.hooksPath .githooks 2>/dev/null || true
  echo "Git hooks path set to .githooks"
else
  echo "No .githooks directory found, skipping hooks"
fi
echo ""

echo "============================================"
echo "  Setup complete"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8050"
echo "  2. Frontend: cd frontend && npm run dev"
echo ""
echo "Postgres is on localhost:55432, Redis on localhost:56379."
echo ""
