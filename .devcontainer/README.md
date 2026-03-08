# Dev Container Setup

Dieser Dev Container bietet eine vollständige Entwicklungsumgebung für den Rental Manager.

## Architektur

- **Reverse Proxy**: Caddy (Port 80, einziger Einstiegspunkt)
- **Infrastructure**: PostgreSQL, Redis, Keycloak (via Docker-outside-of-Docker)
- **Backend**: FastAPI + Celery
- **Frontend**: React + Vite (Build), serviert von Caddy

## Stack starten

```bash
docker compose up -d
```

Logs verfolgen:

```bash
docker compose logs -f
```

Warten Sie, bis Keycloak bereit ist (kann 60–90 Sekunden dauern):

```bash
docker compose logs -f keycloak
```

## Zugriff auf die Services

### Lokal (VS Code Dev Containers)

- App: http://localhost
- API Docs: http://localhost/api/v1/docs
- Keycloak: http://localhost:8081

### GitHub Codespaces

Die URLs werden automatisch von Codespaces generiert und im Terminal angezeigt.

## Hot-Reload-Entwicklung (optional)

Für aktive Backend- oder Frontend-Entwicklung können die Dienste auch direkt auf dem Host gestartet werden:

```bash
# Backend
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separates Terminal)
cd frontend
npm run dev
```

> Im Hot-Reload-Modus läuft das Frontend auf Port 3000, der Vite-Dev-Server proxyt `/api`-Anfragen an Port 8000.

## Stack stoppen

```bash
docker compose down
```

Auch Volumes löschen:

```bash
docker compose down -v
```

## Tipps

- **Logs aller Services**: `docker compose logs -f`
- **Logs eines Services**: `docker compose logs -f [caddy|api|web|keycloak|db|redis]`
- **Stack-Status**: `docker compose ps`

## Demo-Logins

Nach dem ersten Start sind folgende Test-Logins verfügbar:

- **Vermieter**: landlord@example.com / landlord123
- **Mieter**: tenant@example.com / tenant123
