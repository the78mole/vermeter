FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Build-time env vars (baked into the bundle).
# Leave VITE_KEYCLOAK_URL unset so the runtime fallback in oidc.js
# (window.location.origin + "/auth") is used – this works correctly for
# both local dev (http://localhost) and GitHub Codespaces (https://…).
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_KEYCLOAK_URL
ARG VITE_KEYCLOAK_REALM=rental
ARG VITE_KEYCLOAK_CLIENT_ID=rental-frontend

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL
ENV VITE_KEYCLOAK_REALM=$VITE_KEYCLOAK_REALM
ENV VITE_KEYCLOAK_CLIENT_ID=$VITE_KEYCLOAK_CLIENT_ID

RUN npm run build

# ── Serve with Caddy ─────────────────────────────────────────────────────────
FROM caddy:2-alpine

COPY --from=builder /app/dist /srv

# Caddyfile: serve the SPA with HTML5 history-mode fallback
COPY Caddyfile /etc/caddy/Caddyfile
