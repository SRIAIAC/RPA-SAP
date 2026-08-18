# RPA/SAP Ops Console — Oil & Gas Demo

A working prototype of an RPA console for **middle-level management**, built to sit
across **SAP and non-SAP applications**. It demonstrates the pattern described for
the client: managers from different departments trigger and monitor automated
processes, exceptions land in a review queue, and access to each automation is
controlled per department and per management level.

This is a **demo/prototype**: SAP, SCADA, portals, etc. are simulated — there are
no live external system connections. Every workflow's steps, systems and typical
exception reasons are modeled on the realistic Oil & Gas use cases discussed
earlier (invoice matching, maintenance work orders, crude oil receipt
reconciliation, vendor onboarding, HSE incident reporting, etc.).

## Architecture

- **Backend**: FastAPI + SQLModel (SQLite), JWT auth, bcrypt password hashing.
- **Frontend**: React + TypeScript + Vite, no UI framework — hand-built dark theme.
- **Access management**: role-based, scoped by department and management level.

### Departments

Procurement, Maintenance, Finance, HSE, Production — 3 RPA workflows each (15 total),
covering the SAP + non-SAP oil & gas use cases (PO creation, invoice 3-way matching,
vendor onboarding, maintenance work orders, spare parts replenishment, shift handover,
expense processing, fuel reconciliation, contract expiry, HSE incidents, compliance
documents, environmental reporting, daily production reporting, crude oil receipt
reconciliation, sales order processing).

### Access model (four levels)

| Level | Scope |
|---|---|
| **Manager** | Can only run workflows explicitly granted to them. Sees only their own runs/exceptions. |
| **Senior Manager** | Full visibility of their department's workflows, runs and exceptions. Can resolve exceptions. |
| **Department Head** | Same as Senior Manager, plus manages users and grants/revokes workflow access for Managers in their department. |
| **Admin** | Cross-department. Manages all users, all departments, all access grants. |

A **Department Head** can only create/manage `Manager` and `Senior Manager` accounts
in their own department — they cannot create other Department Heads or Admins, and
cannot touch other departments. Only **Admin** has that reach. This mirrors how you'd
want delegated access management to actually work: department leads self-serve their
own team, IT/Admin owns the org-wide picture.

### How a workflow run works

Triggering a workflow (`POST /api/runs`) kicks off a background simulation that walks
through the workflow's real process steps (e.g. *"Lookup PO in SAP MM" → "Lookup GRN
in SAP MM" → "Perform 3-way match"*), ~1 second apart, and finishes either
**Completed** or **Exception** (weighted ~70/30, exception reason drawn from a
realistic pool per workflow). Exceptions land in the **Exception Queue** for a Senior
Manager or above to review and resolve — this is the "human-in-the-loop" pattern from
the earlier use-case discussion.

## Running locally

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The SQLite DB (`backend/rpa_sap.db`) is created and seeded automatically on first
startup — 16 demo users across the 5 departments + 1 global Admin, and all 15
workflows.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` to the backend on
port 8000.

## Demo accounts

All demo accounts use the password **`Demo@123`**.

| Username | Department | Level |
|---|---|---|
| `admin` | — | Admin |
| `asha.rao` | Procurement | Manager |
| `vikram.shah` | Procurement | Senior Manager |
| `neha.kapoor` | Procurement | Department Head |
| `rahul.verma` | Maintenance | Manager |
| `priya.nair` | Maintenance | Senior Manager |
| `suresh.iyer` | Maintenance | Department Head |
| `anjali.mehta` | Finance | Manager |
| `karan.singh` | Finance | Senior Manager |
| `deepa.joshi` | Finance | Department Head |
| `farhan.ali` | HSE | Manager |
| `meera.pillai` | HSE | Senior Manager |
| `omar.hassan` | HSE | Department Head |
| `sanjay.gupta` | Production | Manager |
| `leela.menon` | Production | Senior Manager |
| `arjun.reddy` | Production | Department Head |

Each department's Manager starts with access to 2 of their 3 workflows — log in as
the Department Head (or `admin`) and open **Access Management → Manage access** to
grant the third live, which is a good way to show the access-control story in a demo.

## Project layout

```
backend/
  app/
    main.py          FastAPI app, CORS, startup seeding
    models.py         SQLModel tables (User, Workflow, WorkflowAccess, WorkflowRun, ExceptionItem)
    access.py          RBAC helper functions (single source of truth for permission checks)
    auth.py / deps.py   JWT issuing/verification, FastAPI auth dependencies
    seed_data.py         Demo users + the 15 workflow definitions
    routers/               auth, workflows, runs, exceptions, admin
frontend/
  src/
    api.ts             Typed fetch wrapper for the backend
    auth/AuthContext.tsx
    pages/              Login, Dashboard, RunDetail, Exceptions, Admin
    components/         Layout (sidebar/topbar), RunStatusBadge
```

## Next steps (beyond this prototype)

- Swap the simulated workflow engine for real SAP OData/RFC calls and connectors to
  the non-SAP systems (email, SCADA/historian, portals) per workflow.
- Move from SQLite to Postgres for multi-instance deployment.
- Add SSO (SAML/OIDC) instead of local username/password.
- Add audit logging for every access grant change (who granted what, to whom, when).
