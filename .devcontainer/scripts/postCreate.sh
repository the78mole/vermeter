#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# postCreate.sh  –  Runs ONCE when the devcontainer is first created.
#
# Steps:
#   1. Copy .env.example → .env  (skip if .env already exists)
#   2. Create a Python virtual-env for the backend with uv and install deps.
#   3. Install frontend npm dependencies.
#   4. Pre-pull Docker images so the first postStart.sh is faster.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║  Rental Manager – devcontainer setup       ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# ── 1. Environment file ───────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "✅  Copied .env.example → .env"
else
  echo "ℹ️   .env already exists – skipping copy"
fi

# ── 2. Python virtual-env mit uv ─────────────────────────────────────────────
echo ""
echo "🐍  Setting up Python virtual-env (backend/.venv) with uv…"

(cd backend && uv sync)

echo "✅  Python dependencies installed via uv"

# ── 3. Node.js / npm ─────────────────────────────────────────────────────────
echo ""
echo "📦  Installing frontend npm packages…"
(cd frontend && npm ci --prefer-offline 2>&1 | tail -3)
echo "✅  npm packages installed"

echo ""
echo "🎉  postCreate complete."
echo ""
echo "To start the full stack, run:"
echo "    docker compose up -d"
echo ""
echo "To start the backend with hot-reload instead (after infra is up):"
echo "    cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "To start the frontend dev server instead:"
echo "    cd frontend && npm run dev"
echo ""
