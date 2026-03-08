# vermeter

[![Dokumentation](https://img.shields.io/badge/Doku-GitHub%20Pages-blue?logo=github)](https://the78mole.github.io/vermeter/)
[![Lizenz: AGPL v3](https://img.shields.io/badge/Lizenz-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

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

> **Hinweis:** `docker compose up -d --build` direkt aufzurufen funktioniert nicht zuverlaessig.
> Keycloak benoetigt seine PostgreSQL-Datenbank bereits beim Start, und Docker API ≥ 1.44 ist
> fuer Container mit mehreren Netzwerk-Endpoints erforderlich. Das Setup-Skript erledigt beides automatisch.

Das Setup-Skript ist der einzig unterstuetzte Weg, den Stack auf der gruenen Wiese zu starten:

```bash
./scripts/setup-stack.sh --with-demo-accounts
```

Status danach pruefen:

```bash
docker compose ps
```

Erwartet: `db`, `redis`, `rustfs`, `step-ca`, `keycloak` sind `healthy`; `api`, `web`, `caddy`, `worker`, `beat` sind `Up`.

### 2. Recovery / einzelne Services neu starten

Einen einzelnen Service neu starten:

```bash
docker compose restart <service>
```

Komplettes Teardown und sauberer Neustart:

```bash
docker compose down -v --remove-orphans
./scripts/setup-stack.sh --with-demo-accounts
```

Falls `keycloak/rental-realm.json` geaendert wurde, Keycloak-Image neu bauen:

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
- `CARETAKER`
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
- `CARETAKER`: `hausverwalter@example.com` / `HausverwalterTest2026`
- `LANDLORD`: `demo-landlord@example.com` / `LandlordTest2026`
- `TENANT`: `demo-tenant@example.com` / `TenantTest2026`

### Rollenverhalten in der UI

- `SUPER_ADMIN`: darf `SUPER_ADMIN`, `ADMIN`, `OPERATOR` verwalten
- `ADMIN`: darf `ADMIN` und `OPERATOR` verwalten
- `OPERATOR`: darf nur Vermieter/Mandanten verwalten (keine Admin-Benutzerverwaltung)
- `CARETAKER`: hat Zugriff auf den Vermieter-Bereich (`/landlord/*`) fuer zugewiesene Gebaeude/Wohnungen
- `LANDLORD`: Vermieter-Bereich
- `TENANT`: Mieter-Bereich

## Fachliche Struktur (Gebaeude und Wohnung)

Die Datenstruktur modelliert Immobilien jetzt explizit in zwei Ebenen:

- `Gebaeude` (`Property` in DB/API-Kompatibilitaet)
- `Wohnung` (`Unit` in DB/API-Kompatibilitaet)

Kompatibilitaet:

- Vorhandene Endpunkte `/landlord/properties` und `/landlord/properties/{id}/units` bleiben erhalten.
- Neue semantische Alias-Endpunkte sind ebenfalls vorhanden:
  - `/landlord/buildings`
  - `/landlord/buildings/{building_id}/apartments`

### Mehrere Mieter pro Wohnung (WG / Einzelmietvertraege)

Eine Wohnung kann mehrere Mieter haben, indem mehrere Vertraege auf dieselbe Wohnung verweisen
(z. B. WG mit Einzelmietvertraegen).

- `Contract` referenziert `unit_id` (Wohnung) und `tenant_id`.
- Es gibt keine Ein-Mieter-pro-Wohnung-Restriktion.

### Hausverwalter-Zuweisungen

Hausverwalter koennen zugewiesen werden auf:

- ein gesamtes Gebaeude (`caretaker_building_assignments`), oder
- eine einzelne Wohnung (`caretaker_apartment_assignments`).

Zuweisungs-Endpunkte (durch Vermieter/Admin):

- `POST/DELETE /landlord/buildings/{building_id}/caretakers/{caretaker_id}`
- `POST/DELETE /landlord/apartments/{apartment_id}/caretakers/{caretaker_id}`

## Dev Container (VS Code / GitHub Codespaces)

Das Repository enthaelt einen vollstaendig konfigurierten Dev Container (`.devcontainer/`).

| Einstellung              | Wert                                                                 |
| ------------------------ | -------------------------------------------------------------------- |
| Basis-Image              | `mcr.microsoft.com/devcontainers/base:ubuntu-24.04`                  |
| Standard-Shell           | ZSH mit oh-my-zsh, Theme **fino**                                    |
| Docker                   | Docker-outside-of-Docker (teilt Host-Socket)                         |
| Erforderliche Docker API | **1.50** (wird automatisch in devcontainer und Setup-Skript gesetzt) |

Lifecycle-Skripte:

- **`postCreate.sh`** – laeuft einmalig beim Container-Erstellen: kopiert `.env.example → .env`, installiert Python-venv (`uv sync`), installiert npm-Pakete, setzt ZSH-Theme auf `fino`.
- **`postStart.sh`** – laeuft bei jedem Container-Start.

Nach dem Starten des Dev Containers einfach im integrierten Terminal ausfuehren:

```bash
bash scripts/setup-stack.sh --with-demo-accounts
```

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
