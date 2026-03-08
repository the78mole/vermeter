#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

for svc in keycloak db; do
  if [[ -z "$(docker compose ps -q "$svc")" ]]; then
    echo "Service '$svc' is not running. Start stack first: ./scripts/setup-stack.sh"
    exit 1
  fi
done

# Authenticate kcadm against master realm using container env defaults/overrides.
docker compose exec -T keycloak sh -lc '
  /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080/auth \
    --realm master \
    --user "${KEYCLOAK_ADMIN:-admin}" \
    --password "${KEYCLOAK_ADMIN_PASSWORD:-admin_secret}" \
    >/dev/null
'

ensure_user() {
  local email="$1"
  local first_name="$2"
  local last_name="$3"
  local password="$4"
  local realm_role="$5"

  local user_id
  user_id="$(docker compose exec -T keycloak sh -lc "/opt/keycloak/bin/kcadm.sh get users -r rental -q username=$email --fields id,username" \
    | sed -n 's/.*"id" : "\([^"]*\)".*/\1/p' | head -n1)"

  if [[ -z "$user_id" ]]; then
    docker compose exec -T keycloak sh -lc "/opt/keycloak/bin/kcadm.sh create users -r rental \
      -s username=$email \
      -s email=$email \
      -s enabled=true \
      -s emailVerified=true \
      -s firstName=$first_name \
      -s lastName=$last_name \
      >/dev/null"

    user_id="$(docker compose exec -T keycloak sh -lc "/opt/keycloak/bin/kcadm.sh get users -r rental -q username=$email --fields id,username" \
      | sed -n 's/.*"id" : "\([^"]*\)".*/\1/p' | head -n1)"
  fi

  docker compose exec -T keycloak sh -lc "/opt/keycloak/bin/kcadm.sh update users/$user_id -r rental \
    -s firstName=$first_name -s lastName=$last_name -s email=$email -s enabled=true >/dev/null"

  docker compose exec -T keycloak sh -lc "/opt/keycloak/bin/kcadm.sh set-password -r rental --userid $user_id --new-password '$password'"
  docker compose exec -T keycloak sh -lc "/opt/keycloak/bin/kcadm.sh add-roles -r rental --uid $user_id --rolename $realm_role >/dev/null" || true

  echo "$user_id"
}

SUPER_ID="$(ensure_user super-admin@example.com Super Admin SuperAdminTest2026 admin)"
ADMIN_ID="$(ensure_user test-admin@example.com Test Admin AdminTest2026 admin)"
OPERATOR_ID="$(ensure_user test-operator@example.com Test Operator OperatorTest2026 admin)"
CARETAKER_ID="$(ensure_user hausverwalter@example.com Haus Verwalter HausverwalterTest2026 caretaker)"
LANDLORD_ID="$(ensure_user demo-landlord@example.com Demo Landlord LandlordTest2026 landlord)"
TENANT_ID="$(ensure_user demo-tenant@example.com Demo Tenant TenantTest2026 tenant)"

# Sync admin sub-roles in local DB (required by backend authorization).
docker compose exec -T db sh -lc "psql -v ON_ERROR_STOP=1 -U \"${POSTGRES_USER:-rental}\" -d \"${POSTGRES_DB:-rental_manager}\" <<SQL
DELETE FROM users WHERE email IN ('super-admin@example.com','test-admin@example.com','test-operator@example.com','hausverwalter@example.com');
INSERT INTO users (id, email, hashed_password, full_name, role, admin_role, is_active, created_at, updated_at)
VALUES
  ('$SUPER_ID', 'super-admin@example.com', '', 'Super Admin', 'ADMIN', 'SUPER_ADMIN', true, now(), now()),
  ('$ADMIN_ID', 'test-admin@example.com', '', 'Test Admin', 'ADMIN', 'ADMIN', true, now(), now()),
  ('$OPERATOR_ID', 'test-operator@example.com', '', 'Test Operator', 'ADMIN', 'OPERATOR', true, now(), now()),
  ('$CARETAKER_ID', 'hausverwalter@example.com', '', 'Haus Verwalter', 'CARETAKER', NULL, true, now(), now());
SQL"

echo
echo "Demo accounts ready:"
echo "  SUPER_ADMIN -> super-admin@example.com / SuperAdminTest2026"
echo "  ADMIN       -> test-admin@example.com / AdminTest2026"
echo "  OPERATOR    -> test-operator@example.com / OperatorTest2026"
echo "  CARETAKER   -> hausverwalter@example.com / HausverwalterTest2026"
echo "  LANDLORD    -> demo-landlord@example.com / LandlordTest2026"
echo "  TENANT      -> demo-tenant@example.com / TenantTest2026"
echo
echo "Keycloak IDs:"
echo "  SUPER_ADMIN: $SUPER_ID"
echo "  ADMIN:       $ADMIN_ID"
echo "  OPERATOR:    $OPERATOR_ID"
echo "  CARETAKER:   $CARETAKER_ID"
echo "  LANDLORD:    $LANDLORD_ID"
echo "  TENANT:      $TENANT_ID"
