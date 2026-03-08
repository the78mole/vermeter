# rental-manager

Web-Anwendung fuer die Verwaltung von Vermietung (Vermieter, Mieter, Vertraege, Nebenkosten) mit:

- FastAPI Backend
- React Frontend
- Keycloak (OIDC)
- PostgreSQL + Redis
- Caddy Reverse Proxy

## Initiales Stack-Setup (Docker Compose)

### Automatisches Setup (empfohlen)

Im Projekt-Root ausfuehren:

```bash
./scripts/setup-stack.sh --with-demo-accounts
```

Was das Skript macht:

- baut und startet den kompletten Compose-Stack
- stellt sicher, dass die Postgres-Datenbank `keycloak` existiert (auch bei aelteren Volumes)
- wartet auf kritische Services
- legt Demo-Accounts fuer alle Rollen an

### 1. Stack manuell starten

Im Projekt-Root ausfuehren:

```bash
docker compose up -d --build
```

Status pruefen:

```bash
docker compose ps
```

Erwartet: `db`, `redis`, `rustfs`, `step-ca`, `keycloak` sind `healthy`; `api`, `web`, `caddy`, `worker`, `beat` sind `Up`.

### 2. Recovery bei unvollstaendigem Erststart

Falls `api` oder `caddy` auf `Created` stehen:

```bash
docker compose up -d api caddy
```

Falls `keycloak` unhealthy ist und in den Logs `database "keycloak" does not exist` erscheint:

```bash
./scripts/setup-stack.sh
```

Falls du `keycloak/rental-realm.json` geaendert hast, Keycloak-Image neu bauen:

```bash
docker compose up -d --build keycloak
```

### 3. Zugriff-URLs

Lokal:

- App: `http://localhost`
- Keycloak: `http://localhost/auth`

GitHub Codespaces:

- Forwarded Port `80` oeffnen
- URL verwenden wie: `https://<codespace-name>-80.app.github.dev`

## Beispiel-Accounts fuer alle Rollen

Demo-User fuer alle Rollen anlegen:

- `SUPER_ADMIN`
- `ADMIN`
- `OPERATOR`
- `LANDLORD`
- `TENANT`

Das Skript legt User in Keycloak an und synchronisiert die Admin-Subrollen in PostgreSQL.

```bash
./scripts/create-demo-accounts.sh
```

Standard-Demo-Credentials:

- `SUPER_ADMIN`: `super-admin@example.com` / `SuperAdminTest2026`
- `ADMIN`: `test-admin@example.com` / `AdminTest2026`
- `OPERATOR`: `test-operator@example.com` / `OperatorTest2026`
- `LANDLORD`: `demo-landlord@example.com` / `LandlordTest2026`
- `TENANT`: `demo-tenant@example.com` / `TenantTest2026`

### Rollenverhalten in der UI

- `SUPER_ADMIN`: darf `SUPER_ADMIN`, `ADMIN`, `OPERATOR` verwalten
- `ADMIN`: darf `ADMIN` und `OPERATOR` verwalten
- `OPERATOR`: darf nur Vermieter/Mandanten verwalten (keine Admin-Benutzerverwaltung)
- `LANDLORD`: Vermieter-Bereich
- `TENANT`: Mieter-Bereich

## Backend lokale Entwicklung (ohne Compose)

Das Backend nutzt [uv](https://docs.astral.sh/uv/) fuer Dependency-Management.

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Neue Abhaengigkeit hinzufuegen:

```bash
cd backend
uv add <package>
```
