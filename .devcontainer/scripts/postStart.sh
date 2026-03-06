#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# postStart.sh  –  Runs every time the devcontainer starts (incl. Codespace
#                  resume after suspension).
#
# Steps:
#   1.  Detect whether we are inside GitHub Codespaces.
#   2.  If yes, update .env with the dynamic Codespace URLs for Keycloak and
#       the API, so the Vite dev server picks them up at start time.
#   3.  Start infrastructure services (Postgres, Redis, Keycloak) via Docker
#       Compose.
#   4.  Wait for Keycloak to become healthy.
#   5.  If in Codespaces, patch the Keycloak client's redirect URIs via the
#       Admin REST API (the Codespace hostname is only known at runtime).
#   6.  Run Alembic migrations.
#   7.  Start the FastAPI backend  (uvicorn --reload) in the background.
#   8.  Start the Vite dev server   (npm run dev)     in the background.
#
# Logs:
#   Backend  → /tmp/rental-api.log
#   Frontend → /tmp/rental-frontend.log
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

# Load .env into environment
set -o allexport
# shellcheck source=/dev/null
[[ -f .env ]] && source .env
set +o allexport

POSTGRES_USER="${POSTGRES_USER:-rental}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-rental_secret}"
POSTGRES_DB="${POSTGRES_DB:-rental_manager}"
KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin_secret}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-rental}"
KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-rental-frontend}"

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║  Rental Manager – starting dev stack       ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# ── 1 & 2.  Codespaces URL detection ─────────────────────────────────────────
KC_PUBLIC_URL="http://localhost:8081"
VITE_KC_URL="${VITE_KEYCLOAK_URL:-http://localhost:8081}"

if [[ -n "${CODESPACE_NAME:-}" ]]; then
  FORWARDING_DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  KC_PUBLIC_URL="https://${CODESPACE_NAME}-8081.${FORWARDING_DOMAIN}"
  FRONTEND_ORIGIN="https://${CODESPACE_NAME}-3000.${FORWARDING_DOMAIN}"
  VITE_KC_URL="${KC_PUBLIC_URL}"

  echo "📍 Codespaces detected: ${CODESPACE_NAME}"
  echo "   Keycloak public URL : ${KC_PUBLIC_URL}"
  echo "   Frontend origin     : ${FRONTEND_ORIGIN}"
  echo ""

  # Patch .env so the Vite dev server picks up the correct Keycloak URL.
  # Use a temp file to avoid sed -i portability issues.
  sed "s|^VITE_KEYCLOAK_URL=.*|VITE_KEYCLOAK_URL=${KC_PUBLIC_URL}|" .env > /tmp/.env.tmp
  mv /tmp/.env.tmp .env
fi

# ── 3.  Start infrastructure ──────────────────────────────────────────────────
echo "🐳  Starting infrastructure (Postgres, Redis, Keycloak)…"
docker compose \
  -f .devcontainer/docker-compose.devcontainer.yml \
  up -d --remove-orphans
echo "✅  Infrastructure containers started"
echo ""

# ── 4.  Wait for Postgres ─────────────────────────────────────────────────────
echo "⏳  Waiting for PostgreSQL…"
until docker compose \
    -f .devcontainer/docker-compose.devcontainer.yml \
    exec -T db pg_isready -U "${POSTGRES_USER}" \
    > /dev/null 2>&1; do
  sleep 2
done
echo "✅  PostgreSQL ready"

# ── Wait for Keycloak (takes ~60 s on cold start) ────────────────────────────
echo "⏳  Waiting for Keycloak (may take up to 90 s on first boot)…"
until curl -sf "http://localhost:8081/health/ready" > /dev/null 2>&1; do
  sleep 5
done
echo "✅  Keycloak ready"
echo ""

# ── 5.  Patch Keycloak redirect URIs in Codespaces ───────────────────────────
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  echo "🔑  Patching Keycloak client redirect URIs for Codespaces…"

  # Obtain an admin access token
  ADMIN_TOKEN_RESPONSE=$(curl -sf \
    -d "client_id=admin-cli&grant_type=password&username=${KEYCLOAK_ADMIN}&password=${KEYCLOAK_ADMIN_PASSWORD}" \
    "http://localhost:8081/realms/master/protocol/openid-connect/token")
  ADMIN_TOKEN=$(echo "${ADMIN_TOKEN_RESPONSE}" \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
if 'access_token' not in data:
    print('ERROR: Failed to obtain Keycloak admin token:', data.get('error_description', data), file=sys.stderr)
    sys.exit(1)
print(data['access_token'])
")

  # Resolve the internal UUID of the frontend client
  CLIENT_UUID=$(curl -sf \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "http://localhost:8081/admin/realms/${KEYCLOAK_REALM}/clients?clientId=${KEYCLOAK_CLIENT_ID}" \
    | python3 -c "
import json, sys
clients = json.load(sys.stdin)
if not clients:
    print('ERROR: Keycloak client \"${KEYCLOAK_CLIENT_ID}\" not found in realm \"${KEYCLOAK_REALM}\"', file=sys.stderr)
    sys.exit(1)
print(clients[0]['id'])
")

  # Fetch the current client representation
  CLIENT_JSON=$(curl -sf \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "http://localhost:8081/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}")

  # Write a small Python patcher to a temp file so we can pipe CLIENT_JSON
  # to its stdin while still passing FRONTEND_ORIGIN as a CLI argument.
  cat > /tmp/patch_kc_client.py << 'PYEOF'
import json, sys
frontend_origin = sys.argv[1]
client = json.load(sys.stdin)
redirect_uris = client.setdefault("redirectUris", [])
web_origins   = client.setdefault("webOrigins", [])
new_redirect  = frontend_origin + "/*"
if new_redirect not in redirect_uris:
    redirect_uris.append(new_redirect)
if frontend_origin not in web_origins:
    web_origins.append(frontend_origin)
print(json.dumps(client))
PYEOF

  # Add the Codespace URLs to redirectUris and webOrigins (idempotent)
  UPDATED_CLIENT=$(echo "${CLIENT_JSON}" \
    | python3 /tmp/patch_kc_client.py "${FRONTEND_ORIGIN}")

  # Push the updated representation back
  curl -sf -X PUT \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${UPDATED_CLIENT}" \
    "http://localhost:8081/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}"

  echo "✅  Keycloak client '${KEYCLOAK_CLIENT_ID}' updated"
  echo "    Added redirect URI : ${FRONTEND_ORIGIN}/*"
  echo ""
fi

# ── 6.  Run Alembic migrations ────────────────────────────────────────────────
echo "🗄️   Running database migrations…"
(
  cd backend
  MIGRATION_OUTPUT=$(DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5432/${POSTGRES_DB}" \
    .venv/bin/alembic upgrade head 2>&1) && true   # capture exit code without aborting
  MIGRATION_STATUS=$?
  if [[ ${MIGRATION_STATUS} -ne 0 ]]; then
    if echo "${MIGRATION_OUTPUT}" | grep -qi "no such revision\|can't locate revision\|not found"; then
      echo "⚠️   No Alembic migrations to apply yet – skipping"
    else
      echo "⚠️   Migration warning (exit code ${MIGRATION_STATUS}):"
      echo "${MIGRATION_OUTPUT}" | sed 's/^/    /'
    fi
  else
    echo "${MIGRATION_OUTPUT}" | tail -3
  fi
)
echo ""

# ── 7.  Start FastAPI backend ─────────────────────────────────────────────────
# Kill any leftover process from a previous run
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1

echo "🚀  Starting FastAPI backend on port 8000…"
(
  cd backend
  DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5432/${POSTGRES_DB}" \
  REDIS_URL="redis://127.0.0.1:6379/0" \
  KEYCLOAK_INTERNAL_URL="http://localhost:8081" \
  KEYCLOAK_REALM="${KEYCLOAK_REALM}" \
  ENVIRONMENT="development" \
  nohup .venv/bin/python -m uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 --reload \
    >> /tmp/rental-api.log 2>&1 &
)
echo "✅  Backend started  → http://localhost:8000/docs"
echo "    Logs: tail -f /tmp/rental-api.log"
echo ""

# ── 8.  Start Vite dev server ─────────────────────────────────────────────────
pkill -f "vite" 2>/dev/null || true
sleep 1

echo "⚡  Starting Vite dev server on port 3000…"
(
  cd frontend
  # VITE_KEYCLOAK_URL is read from .env by Vite; we also pass it explicitly.
  VITE_KEYCLOAK_URL="${VITE_KC_URL}" \
  VITE_KEYCLOAK_REALM="${KEYCLOAK_REALM}" \
  VITE_KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID}" \
  nohup npm run dev -- --host 0.0.0.0 \
    >> /tmp/rental-frontend.log 2>&1 &
)
echo "✅  Frontend started → http://localhost:3000"
echo "    Logs: tail -f /tmp/rental-frontend.log"
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "════════════════════════════════════════════"
echo "  Service          URL"
echo "  ───────────────  ─────────────────────────"
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  FWDOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  echo "  Frontend (Vite)  https://${CODESPACE_NAME}-3000.${FWDOMAIN}"
  echo "  API (FastAPI)    https://${CODESPACE_NAME}-8000.${FWDOMAIN}/docs"
  echo "  Keycloak Admin   https://${CODESPACE_NAME}-8081.${FWDOMAIN}"
else
  echo "  Frontend (Vite)  http://localhost:3000"
  echo "  API (FastAPI)    http://localhost:8000/docs"
  echo "  Keycloak Admin   http://localhost:8081"
fi
echo "════════════════════════════════════════════"
echo "  Demo login:"
echo "    Landlord  landlord@example.com / landlord123"
echo "    Tenant    tenant@example.com   / tenant123"
echo "════════════════════════════════════════════"
echo ""
