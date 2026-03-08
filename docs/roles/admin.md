# Admin & Operator

The `ADMIN` role covers platform-level administration. It is subdivided into three
sub-roles that determine how much of the admin area a user can access.

## Sub-role Overview

```mermaid
graph LR
    subgraph "Keycloak Realm Role"
        admin["admin"]
    end

    subgraph "Local DB admin_role"
        SA["SUPER_ADMIN"]
        A["ADMIN"]
        OP["OPERATOR"]
    end

    admin --> SA
    admin --> A
    admin --> OP

    SA -->|"can manage"| SA
    SA -->|"can manage"| A
    SA -->|"can manage"| OP
    A -->|"can manage"| A
    A -->|"can manage"| OP
    OP -->|"NO user mgmt"| note["Landlord &<br/>Tenant management only"]
```

## SUPER_ADMIN

The `SUPER_ADMIN` has full platform control including management of other
`SUPER_ADMIN` accounts. Typically only one or two accounts exist with this level.

**Can do everything an ADMIN can, plus:**

- Create / delete other `SUPER_ADMIN` accounts
- View platform-wide audit entries

**UI Sections:**

- `/admin/dashboard` – Platform overview
- `/admin/users` – All user management (all sub-roles)
- `/admin/landlords` – Landlord management

## ADMIN

`ADMIN` handles day-to-day platform administration. Cannot touch `SUPER_ADMIN` accounts.

**Permissions:**

- Create / edit / deactivate `ADMIN` and `OPERATOR` accounts
- Create and manage `LANDLORD` and `TENANT` accounts
- View all buildings, apartments and contracts (read-only)
- Trigger manual billing runs

**UI Sections:**

- `/admin/dashboard`
- `/admin/users`
- `/admin/landlords`

## OPERATOR

`OPERATOR` is a limited admin role focused on landlord and tenant onboarding.
Operators cannot manage admin-level users at all.

**Permissions:**

- Create / edit `LANDLORD` accounts
- Create / edit `TENANT` accounts
- View all buildings and apartments
- Assign caretakers to objects

**Cannot:**

- Access `/admin/users` for admin-role accounts
- Delete landlords with active buildings

## Typical Workflows

### Creating a new Landlord

```mermaid
flowchart TD
    Admin["ADMIN or OPERATOR"] --> Form["Fill out landlord form<br/>/admin/landlords/new"]
    Form --> KC["User created in Keycloak<br/>(realm role: landlord)"]
    KC --> DB["User synced to local DB<br/>(role: LANDLORD)"]
    DB --> Email["Welcome e-mail sent<br/>(optional)"]
    Email --> Login["Landlord logs in<br/>and sets up portfolio"]
```

### Creating a new Caretaker

```mermaid
flowchart TD
    Admin["ADMIN / OPERATOR"] --> CreateUser["POST /admin/caretakers<br/>Create user in Keycloak<br/>(role: caretaker)"]
    CreateUser --> Assign["Landlord assigns caretaker<br/>to building or apartment"]
    Assign --> Access["Caretaker can now access<br/>assigned objects in /landlord/*"]
```
