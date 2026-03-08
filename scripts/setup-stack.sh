#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

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
docker compose up -d --build

wait_for_service db 180
wait_for_service redis 180
wait_for_service rustfs 180

# Ensure Keycloak database exists even if postgres init scripts did not run
# (e.g. pre-existing volume from an older setup).
echo "Ensuring postgres database 'keycloak' exists..."
docker compose exec -T db sh -lc '
  exists=$(psql -U "${POSTGRES_USER:-rental}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='\''keycloak'\''")
  if [ "$exists" != "1" ]; then
    psql -U "${POSTGRES_USER:-rental}" -d postgres -c "CREATE DATABASE keycloak;"
  fi
'

echo "Starting/restarting Keycloak after DB check..."
docker compose up -d keycloak
wait_for_service keycloak 240

echo "Starting API and edge services..."
docker compose up -d api web caddy worker beat
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
else
  echo "Setup complete. Stack is running."
  echo "Optional: create demo accounts with ./scripts/create-demo-accounts.sh"
fi
