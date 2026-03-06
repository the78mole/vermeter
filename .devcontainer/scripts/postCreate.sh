#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# postCreate.sh  –  Runs ONCE when the devcontainer is first created.
#
# Steps:
#   1. Copy .env.example → .env  (skip if .env already exists)
#   2. Create a Python virtual-env for the backend and install requirements.
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

# ── 2. Python virtual-env ─────────────────────────────────────────────────────
echo ""
echo "🐍  Setting up Python virtual-env (backend/.venv)…"

python3 -m venv backend/.venv

# Upgrade pip silently
backend/.venv/bin/pip install --quiet --upgrade pip

backend/.venv/bin/pip install --quiet -r backend/requirements.txt

echo "✅  Python dependencies installed"

# ── 3. Node.js / npm ─────────────────────────────────────────────────────────
echo ""
echo "📦  Installing frontend npm packages…"
(cd frontend && npm ci --prefer-offline 2>&1 | tail -3)
echo "✅  npm packages installed"

# ── 4. Pre-pull Docker images ─────────────────────────────────────────────────
echo ""
echo "🐳  Pre-pulling infrastructure Docker images…"
docker compose \
  -f .devcontainer/docker-compose.devcontainer.yml \
  pull --quiet
echo "✅  Docker images pulled"

echo ""
echo "🎉  postCreate complete.  The stack will start automatically."
echo "    Run 'bash .devcontainer/scripts/postStart.sh' to restart services."
echo ""
