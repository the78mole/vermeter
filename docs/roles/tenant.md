# Tenant

A `TENANT` has a self-service view of their own rental data. They cannot see other
tenants' data and have no access to administrative or landlord areas.

## What a Tenant Can Do

```mermaid
mindmap
  root((TENANT))
    Contracts
      View own active contracts
      View historical contracts
    Bills
      View own utility bills
      Download PDF bills
    Meter Readings
      View readings for own apartment
      Submit new meter readings
    Profile
      View profile information
```

## Data Scope

A tenant's access is strictly limited to data linked to their own user account:

```mermaid
graph LR
    Tenant["Tenant<br/>(OIDC sub = user_id)"]
    Tenant --> C1["Contract 1<br/>apartment_id=5<br/>tenant_id=T1"]
    Tenant --> C2["Contract 2 (historical)<br/>apartment_id=3<br/>tenant_id=T1"]
    C1 --> Bill1["Bill 2025/Q4"]
    C1 --> Bill2["Bill 2026/Q1"]
    C1 --> Meter["Meter readings<br/>for apartment 5"]
    C2 --> Bill3["Bill 2024/Q4 (historical)"]
```

## Submitting Meter Readings

One of the key self-service features is meter reading submission:

```mermaid
sequenceDiagram
    participant Tenant
    participant API

    Tenant->>API: GET /tenant/contracts (find active apartment)
    API-->>Tenant: Contract with apartment_id

    Tenant->>API: GET /tenant/meters?apartment_id=5
    API-->>Tenant: List of meters (electricity, gas, water)

    Tenant->>API: POST /tenant/meter-readings<br/>{meter_id, value, date}
    API-->>API: Validate: value > previous reading<br/>Validate: tenant has active contract for this apartment
    API-->>Tenant: 201 Created

    Note over Tenant,API: Landlord sees the reading<br/>in their billing dashboard
```

## Tenant Area Navigation

| Page           | Path                     | Description                     |
| -------------- | ------------------------ | ------------------------------- |
| Dashboard      | `/tenant/dashboard`      | Upcoming bills, latest readings |
| Contracts      | `/tenant/contracts`      | All own contracts               |
| Bills          | `/tenant/bills`          | Utility bills with PDF download |
| Meter Readings | `/tenant/meter-readings` | Submit and view readings        |

## Multiple Tenants per Apartment (WG)

Rental Manager supports shared flats (Wohngemeinschaft). Each person in a WG has their
own individual contract linked to the same apartment:

```mermaid
graph TD
    Apt["Apartment 5<br/>(shared flat)"]
    Apt --> C1["Contract A<br/>Tenant: Alice<br/>01.01.2025–31.12.2025"]
    Apt --> C2["Contract B<br/>Tenant: Bob<br/>01.03.2025–ongoing"]
    Apt --> C3["Contract C<br/>Tenant: Carol<br/>01.03.2025–ongoing"]

    C1 --> Alice["Alice sees:<br/>only Contract A + her bills"]
    C2 --> Bob["Bob sees:<br/>only Contract B + his bills"]
    C3 --> Carol["Carol sees:<br/>only Contract C + her bills"]
```

Each tenant sees only their own contract and bills, even when sharing an apartment.
