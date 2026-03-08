# Landlord

A `LANDLORD` manages their own real estate portfolio independently from other landlords.
All data (buildings, apartments, tenants, contracts, meters, billing) is strictly scoped
to the landlord who created it.

## What a Landlord Can Do

```mermaid
mindmap
  root((LANDLORD))
    Buildings
      Create buildings
      Edit building details
      Delete empty buildings
    Apartments
      Create apartments per building
      Edit apartment details
      Assign caretakers
    Tenants
      Invite tenants
      View tenant profiles
    Contracts
      Create contracts
      Link tenant ↔ apartment
      Set term dates and rent
    Meters
      Add utility meters
      Record readings
    Billing
      Run billing calculations
      View and export bills
    Caretakers
      Assign to buildings
      Assign to apartments
      Remove assignments
```

## Portfolio Overview

The landlord dashboard (`/landlord/dashboard`) shows a summary of:

- Total buildings and apartments
- Active vs. vacant apartments
- Pending meter readings
- Recent billing runs

## Managing Buildings & Apartments

See [Domain: Buildings & Apartments](../domain/buildings) for the full data model.

```mermaid
flowchart LR
    Landlord --> B1["Building A<br/>3 Apartments"]
    Landlord --> B2["Building B<br/>6 Apartments"]
    B1 --> A1["Apt 1 – occupied"]
    B1 --> A2["Apt 2 – occupied"]
    B1 --> A3["Apt 3 – vacant"]
    B2 --> A4["Apt 1–6"]
```

## Contract Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft : Landlord creates contract
    Draft --> Active : Start date reached
    Active --> Terminating : Termination notice given
    Terminating --> Ended : End date reached
    Ended --> [*]
    Draft --> [*] : Cancelled before start
```

## Billing Workflow

```mermaid
sequenceDiagram
    participant Landlord
    participant API
    participant Worker

    Landlord->>API: POST /landlord/billing/run
    API->>Worker: Dispatch billing task (Celery)
    Worker->>Worker: Fetch meter readings for period
    Worker->>Worker: Calculate consumption per apartment
    Worker->>Worker: Apply tariffs and allocate service charges
    Worker->>Worker: Generate PDF bill per tenant
    Worker-->>API: Task complete
    API-->>Landlord: Redirect to /landlord/bills
    Landlord->>API: GET /landlord/bills/{id}/pdf
    API-->>Landlord: PDF download
```

## API Reference (Landlord Area)

| Method           | Path                                  | Description                    |
| ---------------- | ------------------------------------- | ------------------------------ |
| `GET`            | `/landlord/dashboard`                 | Portfolio summary              |
| `GET/POST`       | `/landlord/buildings`                 | List / create buildings        |
| `GET/PUT/DELETE` | `/landlord/buildings/{id}`            | Get / update / delete building |
| `GET/POST`       | `/landlord/buildings/{id}/apartments` | List / create apartments       |
| `GET/PUT/DELETE` | `/landlord/apartments/{id}`           | Manage apartment               |
| `GET/POST`       | `/landlord/contracts`                 | List / create contracts        |
| `GET/POST`       | `/landlord/tenants`                   | List / invite tenants          |
| `GET/POST`       | `/landlord/meters`                    | List / create meters           |
| `POST`           | `/landlord/billing/run`               | Trigger billing run            |
| `GET`            | `/landlord/bills`                     | List bills                     |
