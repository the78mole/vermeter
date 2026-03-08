#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Ensure Docker CLI uses an API version the daemon supports.
# Docker API 1.44+ is required for containers with multiple network endpoints.
export DOCKER_API_VERSION="${DOCKER_API_VERSION:-1.50}"

WITH_DEMO_ACCOUNTS=0
if [[ "${1:-}" == "--with-demo-accounts" ]]; then
  WITH_DEMO_ACCOUNTS=1
fi

wait_for_service() {
  local service="$1"
  local timeout_seconds="${2:-180}"
  local waited=0

  while (( waited < timeout_seconds )); do
    local cid status health
    cid="$(docker compose ps -q "$service" || true)"
    if [[ -n "$cid" ]]; then
      status="$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || true)"
      health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$cid" 2>/dev/null || true)"

      if [[ "$status" == "running" ]]; then
        if [[ -z "$health" || "$health" == "healthy" ]]; then
          echo "Service '$service' is ready."
          return 0
        fi
      fi
    fi

    sleep 2
    waited=$((waited + 2))
  done

  echo "Timed out waiting for service '$service'."
  docker compose ps "$service" || true
  return 1
}

echo "Starting Docker Compose stack..."
# Build all images first.
docker compose build

# Step 1: Start infrastructure (DB, Redis, RustFS, step-ca) – but NOT Keycloak.
# Keycloak needs the 'keycloak' database to already exist when it starts.
echo "Starting infrastructure services (db, redis, rustfs, step-ca)..."
docker compose up -d db redis rustfs step-ca web

wait_for_service db 180
wait_for_service redis 180
wait_for_service rustfs 180

# Step 2: Ensure Keycloak database exists.
# The postgres-init.sh init script only runs on a fresh volume. For pre-existing
# volumes or first-time setups where the init didn't create it, we create it here.
echo "Ensuring postgres database 'keycloak' exists..."
docker compose exec -T db sh -lc '
  exists=$(psql -U "${POSTGRES_USER:-rental}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='\''keycloak'\''")
  if [ "$exists" != "1" ]; then
    psql -U "${POSTGRES_USER:-rental}" -d postgres -c "CREATE DATABASE keycloak;"
    echo "Created database keycloak."
  else
    echo "Database keycloak already exists."
  fi
'

# Step 3: Start Keycloak now that its database is guaranteed to exist.
echo "Starting Keycloak..."
docker compose up -d keycloak
wait_for_service keycloak 240

# Step 4: Start API and edge services.
echo "Starting API and edge services..."
docker compose up -d api caddy worker beat
wait_for_service api 180
wait_for_service web 120
wait_for_service caddy 120

docker compose ps

if (( WITH_DEMO_ACCOUNTS == 1 )); then
  echo
  echo "Creating demo accounts..."
  "$REPO_ROOT/scripts/create-demo-accounts.sh"
fi

echo
if (( WITH_DEMO_ACCOUNTS == 1 )); then
  echo "Setup complete. Stack is running and demo accounts are ready."
  echo
  echo "Landing Page: http://localhost/landing"
else
  echo "Setup complete. Stack is running."
  echo "Optional: create demo accounts with ./scripts/create-demo-accounts.sh"
fi
