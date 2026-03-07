# Benutzerrollen & Mandantenstruktur

## Überblick

Der Rental Manager ist eine Mehrmandanten-Plattform (Multi-Tenant SaaS). Es gibt zwei
grundlegend verschiedene Nutzergruppen:

- **Plattform-Ebene**: Betreiber der Software
- **Mandanten-Ebene**: Kunden der Plattform (Hausverwaltungen, private Vermieter, Hausmeisterdienste)
- **Mieter-Ebene**: Endnutzer, die eine Wohneinheit gemietet haben

---

## Rollenübersicht

| Rolle          | Keycloak-Rolle    | Ebene                           | Beschreibung                                                |
| -------------- | ----------------- | ------------------------------- | ----------------------------------------------------------- |
| Platform-Admin | `platform_admin`  | Plattform                       | Zugang zu allen Mandanten, System-Konfiguration             |
| Mandant-Admin  | `mandant_admin`   | Mandant                         | Verwaltet seinen Mandanten und alle Benutzer darin          |
| Manager        | `mandant_manager` | Mandant                         | Normaler Vermieter-Benutzer; verwaltet Objekte und Verträge |
| Caretaker      | `caretaker`       | Mandant (mandantenübergreifend) | Hausmeister; lesen/schreiben in zugewiesenen Mandanten      |
| Mieter         | `renter`          | Mieter                          | Sieht eigene Verträge, Zählerstände und Abrechnungen        |

---

## Mandantenmodell

```mermaid
erDiagram
    Platform ||--o{ Mandant : betreibt

    Mandant {
        uuid id
        string name
        string type
    }
    Mandant ||--o{ MandantUser : hat
    Mandant ||--o{ Property : besitzt
    Mandant ||--o{ MandantAccess : gewährt

    MandantUser {
        uuid id
        uuid mandant_id
        uuid keycloak_sub
        enum role
    }

    MandantAccess {
        uuid id
        uuid mandant_id
        uuid grantee_mandant_id
        enum access_level
    }

    Property ||--o{ Unit : enthält
    Unit ||--o{ Contract : hat
    Unit ||--o{ Meter : hat
    Contract }o--|| Renter : abgeschlossen_mit
    Meter ||--o{ MeterReading : hat

    Renter {
        uuid id
        string email
        string full_name
        uuid keycloak_sub
    }
```

---

## Rollenbeziehungen und Zugriffsrechte

```mermaid
graph TD
    PA[🔧 Platform Admin<br/><i>platform_admin</i>]
    MA[👔 Mandant Admin<br/><i>mandant_admin</i>]
    MM[🏢 Manager<br/><i>mandant_manager</i>]
    CT[🔑 Caretaker<br/><i>caretaker</i>]
    RN[🏠 Mieter<br/><i>renter</i>]

    PA -->|verwaltet alle| MA
    PA -->|sieht alle| Mandant1[Mandant A<br/>Hausverwaltung GmbH]
    PA -->|sieht alle| Mandant2[Mandant B<br/>Privater Vermieter]
    PA -->|sieht alle| Mandant3[Mandant C<br/>Hausmeisterservice]

    MA -->|verwaltet| Mandant1
    MA -->|erstellt/löscht| MM
    MA -->|erstellt/löscht| CT

    MM -->|verwaltet Objekte in| Mandant1

    Mandant3 -->|MandantAccess| Mandant1
    Mandant3 -->|MandantAccess| Mandant2
    CT -->|gehört zu| Mandant3
    CT -->|eingeschränkter Zugang zu| Mandant1
    CT -->|eingeschränkter Zugang zu| Mandant2

    RN -->|sieht eigene Daten in| Mandant1
    RN -->|sieht eigene Daten in| Mandant2

    style PA fill:#c0392b,color:#fff
    style MA fill:#2980b9,color:#fff
    style MM fill:#27ae60,color:#fff
    style CT fill:#f39c12,color:#fff
    style RN fill:#8e44ad,color:#fff
```

---

## Mandantentypen

```mermaid
graph LR
    subgraph "Typ: Hausverwaltung (gewerblich)"
        HV_Admin[Mandant Admin]
        HV_Mgr1[Manager 1]
        HV_Mgr2[Manager 2]
        HV_Admin --> HV_Mgr1
        HV_Admin --> HV_Mgr2
    end

    subgraph "Typ: Privater Vermieter"
        PV_Admin[Mandant Admin<br/><i>einziger User</i>]
    end

    subgraph "Typ: Hausmeisterservice"
        HS_Admin[Mandant Admin]
        HS_CT1[Caretaker 1]
        HS_CT2[Caretaker 2]
        HS_Admin --> HS_CT1
        HS_Admin --> HS_CT2
    end

    subgraph "Objekte anderer Mandanten"
        Obj_A[Objekte Mandant A]
        Obj_B[Objekte Mandant B]
    end

    HS_CT1 -.->|MandantAccess| Obj_A
    HS_CT2 -.->|MandantAccess| Obj_A
    HS_CT2 -.->|MandantAccess| Obj_B
```

---

## MandantAccess: Hausmeisterservice-Sonderfall

Ein Hausmeisterservice ist ein eigenständiger Mandant (`Typ: SERVICE_PROVIDER`).
Über die `MandantAccess`-Tabelle erhält er eingeschränkten Zugriff auf Objekte anderer Mandanten.

```mermaid
sequenceDiagram
    participant HA as Hausmeister-<br/>Mandant Admin
    participant PA as Platform Admin /<br/>Ziel-Mandant Admin
    participant DB as Datenbank

    HA->>PA: Zugriffsanfrage für Mandant X
    PA->>DB: INSERT MandantAccess(grantee=HS, target=X, level=READ_WRITE)
    DB-->>PA: OK
    PA-->>HA: Zugang gewährt

    Note over HA,DB: Caretaker des HS-Mandanten<br/>sieht jetzt Objekte von Mandant X
```

---

## Zugriffsmatrix

| Aktion                 | platform_admin | mandant_admin | mandant_manager | caretaker |   renter    |
| ---------------------- | :------------: | :-----------: | :-------------: | :-------: | :---------: |
| Mandanten verwalten    |       ✅       |      ❌       |       ❌        |    ❌     |     ❌      |
| Mandant-User erstellen |       ✅       | ✅ (eigener)  |       ❌        |    ❌     |     ❌      |
| MandantAccess vergeben |       ✅       | ✅ (eigener)  |       ❌        |    ❌     |     ❌      |
| Immobilien verwalten   |       ✅       |      ✅       |       ✅        |  👁️ read  |     ❌      |
| Verträge verwalten     |       ✅       |      ✅       |       ✅        |  👁️ read  |  👁️ eigene  |
| Zählerstände erfassen  |       ✅       |      ✅       |       ✅        |    ✅     | ✅ (eigene) |
| Nebenkostenabrechnung  |       ✅       |      ✅       |       ✅        |    ❌     |  👁️ eigene  |
| Mieter verwalten       |       ✅       |      ✅       |       ✅        |    ❌     |     ❌      |

---

## Begriffsdefinitionen

| Begriff               | Definition                                                                                                                                                              |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mandant**           | Organisationseinheit auf der Plattform (Kunde). Entspricht einem Unternehmen oder einer Privatperson als Vermieter.                                                     |
| **MandantUser**       | Login-fähiger Benutzer, der zu einem Mandanten gehört. Hat eine Rolle innerhalb des Mandanten.                                                                          |
| **Caretaker**         | Hausmeister. Gehört zu einem Dienstleister-Mandanten, hat aber delegierten Zugang zu Objekten anderer Mandanten.                                                        |
| **Mieter** (`Renter`) | Person, die eine Wohneinheit gemietet hat. Kann (optional) einen Keycloak-Account haben für Self-Service. Bewusste Abgrenzung von `Tenant` (= Mandant in SaaS-Kontext). |
| **MandantAccess**     | Delegierter, eingeschränkter Zugang eines Mandanten zu Objekten eines anderen Mandanten.                                                                                |
| **Property**          | Immobilie (Gebäude). Gehört zu einem Mandanten.                                                                                                                         |
| **Unit**              | Mieteinheit innerhalb einer Immobilie (Wohnung, Gewerbeeinheit).                                                                                                        |
