# Contracts & Billing

## Contract Model

A contract links a **tenant** to an **apartment** for a defined period and records the
agreed rent. There is no one-tenant-per-apartment restriction; multiple concurrent
contracts are supported for shared flats.

```mermaid
erDiagram
    APARTMENT ||--o{ CONTRACT : "has"
    USER ||--o{ CONTRACT : "tenant_id"
    CONTRACT {
        uuid id
        uuid apartment_id
        uuid tenant_id
        date start_date
        date end_date
        decimal monthly_rent
        decimal deposit
        string status
    }
    CONTRACT ||--o{ BILL : "generates"
```

## Contract Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft : Landlord creates
    Draft --> Active : start_date reached<br/>(or manual activation)
    Active --> Terminating : termination_date set
    Terminating --> Ended : end_date reached
    Active --> Ended : immediate termination
    Draft --> Cancelled : cancelled before start
    Ended --> [*]
    Cancelled --> [*]
```

## Meters & Readings

Each apartment can have multiple utility meters (electricity, gas, water, heat, etc.).
Readings are recorded either by the tenant (self-service) or by the landlord/caretaker.

```mermaid
graph TD
    Apartment --> M1["Electricity Meter<br/>unit: kWh"]
    Apartment --> M2["Gas Meter<br/>unit: m³"]
    Apartment --> M3["Cold Water<br/>unit: m³"]
    Apartment --> M4["Hot Water<br/>unit: m³"]

    M1 --> R1["Reading 01.01.2025<br/>12340 kWh"]
    M1 --> R2["Reading 01.04.2025<br/>12895 kWh"]
    M1 --> R3["Reading 01.07.2025<br/>13210 kWh"]
    M1 --> R4["Reading 01.10.2025<br/>13680 kWh"]
    M1 --> R5["Reading 01.01.2026<br/>14200 kWh"]
```

### Meter Reading Validation

```mermaid
flowchart TD
    Submit["POST /tenant/meter-readings<br/>{meter_id, value, date}"] --> V1{"value > previous<br/>reading?"}
    V1 -->|No| Err1["400 Bad Request<br/>Value must be ascending"]
    V1 -->|Yes| V2{"Tenant has active<br/>contract for this<br/>apartment?"}
    V2 -->|No| Err2["403 Forbidden"]
    V2 -->|Yes| Save["Store reading<br/>201 Created"]
    Save --> Notify["Notify landlord<br/>(optional webhook)"]
```

## Billing Calculation

Billing runs are triggered manually by the landlord or automatically by the Celery Beat
scheduler. A run covers a defined billing period and processes all apartments with
active contracts.

```mermaid
flowchart TD
    Trigger["POST /landlord/billing/run<br/>{period_start, period_end}"] --> Task["Celery task<br/>dispatched"]

    Task --> FetchContracts["Fetch active contracts<br/>for billing period"]
    FetchContracts --> PerContract["For each contract"]

    PerContract --> Readings["Fetch meter readings<br/>start + end of period"]
    Readings --> Consumption["Calculate consumption<br/>per meter type"]
    Consumption --> Tariff["Apply tariffs<br/>+ service charges"]
    Tariff --> Share["Calculate tenant's<br/>proportion (if WG)"]
    Share --> CreateBill["Create BILL record<br/>+ PDF generation"]

    CreateBill --> Done["All bills stored<br/>Status: PENDING → SENT"]
```

### Bill PDF Generation

Bills are stored as PDF files in the S3-compatible RustFS storage and can be
downloaded by both the landlord and the relevant tenant.

```mermaid
sequenceDiagram
    participant Tenant
    participant API
    participant S3 as RustFS (S3)

    Tenant->>API: GET /tenant/bills/{id}/pdf
    API->>API: Verify: bill.contract.tenant_id == current user
    API->>S3: GetObject bills/{id}.pdf
    S3-->>API: PDF bytes
    API-->>Tenant: 200 application/pdf
```

## Billing Period & Allocation

For shared flats, service charges (Nebenkosten) are allocated proportionally:

| Tenant | Contract Start | Monthly Rent | Share |
| ------ | -------------- | ------------ | ----- |
| Alice  | 01.01.2025     | €450         | 33 %  |
| Bob    | 01.03.2025     | €430         | 33 %  |
| Carol  | 01.06.2025     | €420         | 34 %  |

The exact allocation model (equal shares vs. rent-weighted) is configurable per
billing run.

## API Reference

| Method     | Path                       | Description               |
| ---------- | -------------------------- | ------------------------- |
| `GET/POST` | `/landlord/contracts`      | List / create contracts   |
| `GET/PUT`  | `/landlord/contracts/{id}` | Get / update contract     |
| `GET/POST` | `/landlord/meters`         | List / create meters      |
| `POST`     | `/landlord/meter-readings` | Record a meter reading    |
| `POST`     | `/landlord/billing/run`    | Trigger billing run       |
| `GET`      | `/landlord/bills`          | List all bills            |
| `GET`      | `/landlord/bills/{id}/pdf` | Download bill PDF         |
| `GET`      | `/tenant/contracts`        | Tenant: own contracts     |
| `GET`      | `/tenant/bills`            | Tenant: own bills         |
| `GET`      | `/tenant/bills/{id}/pdf`   | Tenant: download own bill |
| `POST`     | `/tenant/meter-readings`   | Tenant: submit reading    |
