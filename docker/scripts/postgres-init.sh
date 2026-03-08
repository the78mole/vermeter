#!/usr/bin/env bash
# Create multiple PostgreSQL databases for the same postgres user.
# Mount this file into /docker-entrypoint-initdb.d/ in the postgres container.
set -e

function create_db() {
  local database=$1
  echo "Creating database: $database"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE ${database}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${database}')\\gexec
    GRANT ALL PRIVILEGES ON DATABASE ${database} TO ${POSTGRES_USER};
EOSQL
}

# Always create the application DB (already created by POSTGRES_DB env var, but safe to call again)
create_db "${POSTGRES_DB:-rental_manager}"
# Create the Keycloak DB
create_db "keycloak"
