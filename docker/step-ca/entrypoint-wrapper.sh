#!/bin/bash
# Wrapper entrypoint for smallstep/step-ca.
# Writes the STEPCA_PASSWORD env var to a temp file so that
# DOCKER_STEPCA_INIT_PASSWORD_FILE can point to a real file path rather than
# relying on Docker secret bind-mounts (which can be unreliable in DooD setups).
set -e

PW_FILE="$(mktemp /tmp/stepca_password.XXXXXX)"
echo -n "${STEPCA_PASSWORD:-StepCA_Dev_Secret_2024!}" > "$PW_FILE"
export DOCKER_STEPCA_INIT_PASSWORD_FILE="$PW_FILE"

# Hand off to the upstream step-ca entrypoint
exec /bin/bash /entrypoint.sh "$@"
