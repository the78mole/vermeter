# Domain Model

Rental Manager's domain is built around a two-level property hierarchy and a
contract-centric tenancy model.

## Entity Relationship Overview

```mermaid
erDiagram
    USER {
        uuid id PK
        string email
        string role
        string admin_role
    }

    BUILDING {
        uuid id PK
        uuid landlord_id FK
        string name
        string address
    }

    APARTMENT {
        uuid id PK
        uuid building_id FK
        string name
        int floor
        float area_sqm
    }

    CONTRACT {
        uuid id PK
        uuid apartment_id FK
        uuid tenant_id FK
        date start_date
        date end_date
        decimal monthly_rent
    }

    METER {
        uuid id PK
        uuid apartment_id FK
        string type
        string unit
    }

    METER_READING {
        uuid id PK
        uuid meter_id FK
        uuid submitted_by FK
        decimal value
        date reading_date
    }

    BILL {
        uuid id PK
        uuid contract_id FK
        date period_start
        date period_end
        decimal amount
        string status
    }

    CARETAKER_BUILDING_ASSIGNMENT {
        uuid caretaker_id FK
        uuid building_id FK
    }

    CARETAKER_APARTMENT_ASSIGNMENT {
        uuid caretaker_id FK
        uuid apartment_id FK
    }

    USER ||--o{ BUILDING : "owns (landlord)"
    BUILDING ||--o{ APARTMENT : "contains"
    APARTMENT ||--o{ CONTRACT : "covered by"
    USER ||--o{ CONTRACT : "tenant in"
    APARTMENT ||--o{ METER : "has"
    METER ||--o{ METER_READING : "has"
    CONTRACT ||--o{ BILL : "generates"
    USER ||--o{ CARETAKER_BUILDING_ASSIGNMENT : "caretaker"
    BUILDING ||--o{ CARETAKER_BUILDING_ASSIGNMENT : "assigned"
    USER ||--o{ CARETAKER_APARTMENT_ASSIGNMENT : "caretaker"
    APARTMENT ||--o{ CARETAKER_APARTMENT_ASSIGNMENT : "assigned"
```

## Domain Sections

| Section                               | Description                                                  |
| ------------------------------------- | ------------------------------------------------------------ |
| [Buildings & Apartments](./buildings) | Property hierarchy, caretaker assignment model, WG scenarios |
| [Contracts & Billing](./contracts)    | Contract lifecycle, meter readings, billing calculation      |
