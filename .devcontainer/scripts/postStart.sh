#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# postStart.sh  –  Runs every time the devcontainer starts (incl. Codespace
#                  resume after suspension).
#
# This script only updates environment variables for Codespaces.
# The user manually starts the infrastructure and dev servers.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

# Load .env into environment
set -o allexport
# shellcheck source=/dev/null
[[ -f .env ]] && source .env
set +o allexport

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║  Rental Manager – Dev Container Ready      ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# ── Codespaces URL detection ──────────────────────────────────────────────────
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  FORWARDING_DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  KC_PUBLIC_URL="https://${CODESPACE_NAME}-80.${FORWARDING_DOMAIN}/auth"
  FRONTEND_ORIGIN="https://${CODESPACE_NAME}-80.${FORWARDING_DOMAIN}"

  echo "📍 Codespaces detected: ${CODESPACE_NAME}"
  echo "   Updating .env with Codespace URLs..."
  echo ""

  # Patch .env so the Vite dev server picks up the correct Keycloak URL.
  sed "s|^VITE_KEYCLOAK_URL=.*|VITE_KEYCLOAK_URL=${KC_PUBLIC_URL}|" .env > /tmp/.env.tmp
  mv /tmp/.env.tmp .env
  echo "✅  .env updated with Codespace URLs"
  echo ""
fi

# ── Manual Start Instructions ─────────────────────────────────────────────────
echo "🚀 To start the stack:"
echo ""
echo "1️⃣  Start the full stack:"
echo "    docker compose up -d"
echo ""
echo "   (For hot-reload development, build and run backend/frontend directly:)"
echo "   cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo "   cd frontend && npm run dev"
echo ""
echo "════════════════════════════════════════════"
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  FWDOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  echo "  App:        https://${CODESPACE_NAME}-80.${FWDOMAIN}"
  echo "  API Docs:   https://${CODESPACE_NAME}-80.${FWDOMAIN}/api/v1/docs"
  echo "  Keycloak:   https://${CODESPACE_NAME}-80.${FWDOMAIN}/auth"
else
  echo "  App:        http://localhost"
  echo "  API Docs:   http://localhost/api/v1/docs"
  echo "  Keycloak:   http://localhost/auth"
fi
echo "════════════════════════════════════════════"
echo ""
