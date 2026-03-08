# Benutzerrollen und Zugriffsmodell

## Überblick

Der Rental Manager verwendet aktuell folgende fachliche Rollen:

- `ADMIN` (mit Subrollen `SUPER_ADMIN`, `ADMIN`, `OPERATOR`)
- `LANDLORD`
- `CARETAKER` (Hausverwalter)
- `TENANT`

Authentifizierung erfolgt ueber Keycloak (OIDC), die Autorisierung in der API ueber
lokale Rollen und Subrollen.

## Rollenmodell

### 1. Plattform-Adminrolle (`ADMIN`)

`ADMIN` ist die Plattformrolle und wird über `admin_role` differenziert:

- `SUPER_ADMIN`: darf alle Admin-Benutzer verwalten (`SUPER_ADMIN`, `ADMIN`, `OPERATOR`)
- `ADMIN`: darf `ADMIN` und `OPERATOR` verwalten
- `OPERATOR`: kein Admin-User-Management, Fokus auf Vermieter-/Mandantenverwaltung

### 2. Vermieterrolle (`LANDLORD`)

- verwaltet eigene Gebaeude/Wohnungen
- verwaltet Vertraege, Zaehler, Ablesungen, Abrechnungen im eigenen Bestand
- kann Hausverwalter-Zuweisungen steuern

### 3. Hausverwalterrolle (`CARETAKER`)

- arbeitet im Vermieter-Bereich (`/landlord/*`), aber nur auf zugewiesenen Objekten
- darf keine globale Gebaeudestruktur aendern (z. B. keine neuen Gebaeude anlegen)
- Zugriff wird ueber Zuweisung auf Gebaeude- oder Wohnungsebene erteilt

Anlage/Verwaltung von Hausverwaltern erfolgt ueber Admin-API:

- `GET /admin/caretakers`
- `POST /admin/caretakers`

### 4. Mieterrolle (`TENANT`)

- sieht eigene Vertraege, eigene Abrechnungen und eigene Zaehlerdaten
- kann eigene Zaehlerstaende erfassen

## Objektstruktur: Gebaeude und Wohnungen

Die Datenstruktur ist zweistufig:

- `Building` fachlich = `Property` technisch
- `Apartment` fachlich = `Unit` technisch

Damit bleiben bestehende Endpunkte kompatibel und neue, semantische Endpunkte sind zusaetzlich verfuegbar.

### Endpunkt-Kompatibilitaet

Bestehend:

- `/landlord/properties`
- `/landlord/properties/{property_id}/units`

Neu (Alias):

- `/landlord/buildings`
- `/landlord/buildings/{building_id}/apartments`

## Mehrere Mieter pro Wohnung (WG / Einzelmietvertraege)

Das System unterstuetzt mehrere Mieter in derselben Wohnung:

- Jeder Vertrag referenziert `unit_id` (Wohnung) und `tenant_id` (Mieter)
- Es gibt keine 1:1-Beschraenkung zwischen Wohnung und Mieter
- Dadurch sind mehrere Einzelmietvertraege pro Wohnung moeglich (z. B. WG)

## Hausverwalter-Zuweisungsmodell

Hausverwalter koennen auf zwei Ebenen zugewiesen werden:

- Gebaeudeweit: `caretaker_building_assignments`
- Wohnungsbezogen: `caretaker_apartment_assignments`

Verwaltungsendpunkte:

- `POST /landlord/buildings/{building_id}/caretakers/{caretaker_id}`
- `DELETE /landlord/buildings/{building_id}/caretakers/{caretaker_id}`
- `POST /landlord/apartments/{apartment_id}/caretakers/{caretaker_id}`
- `DELETE /landlord/apartments/{apartment_id}/caretakers/{caretaker_id}`

## Kurzmatrix (vereinfacht)

| Aktion                                       | SUPER_ADMIN |                   ADMIN | OPERATOR |    LANDLORD |              CARETAKER |                  TENANT |
| -------------------------------------------- | ----------: | ----------------------: | -------: | ----------: | ---------------------: | ----------------------: |
| Admin-Benutzer verwalten                     |   ja (alle) | ja (`ADMIN`,`OPERATOR`) |     nein |        nein |                   nein |                    nein |
| Vermieter verwalten                          |          ja |                      ja |       ja |        nein |                   nein |                    nein |
| Gebaeude/Wohnungen strukturell aendern       |          ja |                      ja |       ja | ja (eigene) |                   nein |                    nein |
| Zaehler/Ablesungen auf zugewiesenen Objekten |          ja |                      ja |       ja | ja (eigene) |        ja (zugewiesen) | eingeschraenkt (eigene) |
| Eigene Vertrags-/Abrechnungsdaten sehen      |    optional |                optional | optional |          ja | teilweise (zugewiesen) |                      ja |

Hinweis: Detailregeln sind in den API-Dependencies und Route-Guards umgesetzt (z. B. `require_admin_manager`, `require_landlord_or_caretaker`).
