FROM smallstep/step-ca:latest

# Allow passing the CA password via the STEPCA_PASSWORD environment variable.
USER root
COPY --chmod=755 entrypoint-wrapper.sh /usr/local/bin/entrypoint-wrapper.sh
# Restore the unprivileged step user from the base image
USER step

ENTRYPOINT ["/usr/local/bin/entrypoint-wrapper.sh"]
