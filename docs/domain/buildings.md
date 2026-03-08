# Buildings & Apartments

Real estate in Rental Manager is modelled in two explicit layers:

| Concept   | DB/API Technical Name            | Description                     |
| --------- | -------------------------------- | ------------------------------- |
| Building  | `Property` (legacy) / `Building` | Physical building structure     |
| Apartment | `Unit` (legacy) / `Apartment`    | Rentable unit inside a building |

::: note API Compatibility
Both naming conventions are supported. Legacy endpoints (`/properties`, `/units`) remain
fully functional alongside the semantic aliases (`/buildings`, `/apartments`).
:::

## Two-Level Hierarchy

```mermaid
graph TD
    L["LANDLORD<br/>Anna Müller"] --> B1["Building<br/>Musterstraße 1<br/>(3 floors)"]
    L --> B2["Building<br/>Beispielweg 5<br/>(2 floors)"]

    B1 --> A1["Apt 1OG-L<br/>65 m²"]
    B1 --> A2["Apt 1OG-R<br/>72 m²"]
    B1 --> A3["Apt 2OG<br/>80 m²"]

    B2 --> A4["Apt EG<br/>55 m²"]
    B2 --> A5["Apt 1OG<br/>68 m²"]
```

## Role Access to Buildings & Apartments

```mermaid
graph LR
    subgraph Roles
        SA["SUPER_ADMIN / ADMIN / OPERATOR"]
        LL["LANDLORD"]
        CT["CARETAKER"]
        TN["TENANT"]
    end

    subgraph Data
        AllBuildings["All buildings in system"]
        OwnBuildings["Own buildings only"]
        AssignedBuildings["Assigned buildings only"]
        AssignedApts["Assigned apartments only"]
        NoAccess["No building access"]
    end

    SA -->|"read + write"| AllBuildings
    LL -->|"full CRUD"| OwnBuildings
    CT -->|"read only"| AssignedBuildings
    CT -->|"read only"| AssignedApts
    TN --> NoAccess
```

## Caretaker Assignment

Caretakers have a two-tier assignment model. A building-level assignment grants access
to all apartments within that building. An apartment-level assignment is more granular.

```mermaid
graph TD
    subgraph "Building-level assignment"
        B_A["Building A<br/>Musterstr. 1"] --> a1["Apt 1"]
        B_A --> a2["Apt 2"]
        B_A --> a3["Apt 3"]
        CK1["Caretaker Klaus"] -.->|"sees all 3 apts"| B_A
    end

    subgraph "Apartment-level assignment"
        B_B["Building B<br/>Beispielweg 5"] --> a4["Apt 1"]
        B_B --> a5["Apt 2"]
        B_B --> a6["Apt 3"]
        CK2["Caretaker Maria"] -.->|"sees only"| a5
    end

    subgraph "Mixed assignment"
        B_C["Building C"] --> a7["Apt 1"]
        B_C --> a8["Apt 2"]
        CK3["Caretaker Peter"] -.->|"whole building"| B_C
        CK3 -.->|"+ specific apt elsewhere"| a5
    end
```

### Assignment API

```http
# Assign caretaker to a whole building
POST /landlord/buildings/{building_id}/caretakers/{caretaker_id}

# Remove building assignment
DELETE /landlord/buildings/{building_id}/caretakers/{caretaker_id}

# Assign caretaker to a single apartment
POST /landlord/apartments/{apartment_id}/caretakers/{caretaker_id}

# Remove apartment assignment
DELETE /landlord/apartments/{apartment_id}/caretakers/{caretaker_id}
```

## Shared Flats (WG / Wohngemeinschaft)

An apartment can have multiple active contracts simultaneously, one per tenant.
This enables individual billing for shared flats:

```mermaid
graph TD
    Apt["Apartment 2OG<br/>Musterstr. 1<br/>80 m²"]

    Apt --> C1["Contract Alice<br/>01.01.2025 – ongoing<br/>€450/month"]
    Apt --> C2["Contract Bob<br/>01.03.2025 – ongoing<br/>€430/month"]
    Apt --> C3["Contract Carol<br/>01.06.2025 – 31.05.2026<br/>€420/month"]

    C1 --> B1["Alice's bills<br/>Q1–Q4 2025"]
    C2 --> B2["Bob's bills<br/>Q2–Q4 2025"]
    C3 --> B3["Carol's bills<br/>Q3 2025 – Q2 2026"]
```

Each tenant receives their own utility bill based on their contract's share of
consumption. Meters are linked to the apartment; readings are shared across all
active contracts.

## API Endpoint Reference

| Method           | Path (semantic)                       | Path (legacy)                     | Description             |
| ---------------- | ------------------------------------- | --------------------------------- | ----------------------- |
| `GET/POST`       | `/landlord/buildings`                 | `/landlord/properties`            | List / create buildings |
| `GET/PUT/DELETE` | `/landlord/buildings/{id}`            | `/landlord/properties/{id}`       | Single building         |
| `GET/POST`       | `/landlord/buildings/{id}/apartments` | `/landlord/properties/{id}/units` | Apartments in building  |
| `GET/PUT/DELETE` | `/landlord/apartments/{id}`           | `/landlord/units/{id}`            | Single apartment        |
