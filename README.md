# AI-Powered Oil & Gas Automation Operations Platform

> **This project uses synthetic data and mock integrations. No production SAP
> system, real company data, or external API credentials are required.**
> Everything below runs entirely on your machine (or in Docker) with zero
> outbound calls to any third-party service.

## 1. What this is

A working prototype of an enterprise automation operations platform for
**middle-level management** in an Oil & Gas company, demonstrating how RPA,
AI, business rules, human approval, and event-driven automation orchestrate
across SAP and non-SAP systems. Managers trigger and monitor automated
workflows; exceptions that need judgment land in a review queue with full
AI/rules explainability; every action is audited; and management gets
live analytics on automation rate and hours saved.

It began as a smaller "RPA console" prototype (see `CLAUDE.md` for that
history) and was incrementally upgraded — without breaking the original
RBAC, workflow definitions, or UI — into the platform described here.

## 2. Business problem

Oil & Gas back-office and field operations teams run dozens of repetitive,
cross-system processes — invoice 3-way matching, maintenance work orders,
crude receipt reconciliation, vendor onboarding, HSE incident triage — that
today are manual, span SAP and half a dozen non-SAP systems (SCADA, terminal
management, CRM, supplier portals, email), and only escalate to a human when
something doesn't match. This platform demonstrates the target operating
model: **AI extracts and classifies, deterministic business rules decide,
RPA executes the mechanical steps, and humans are pulled in only for the
exceptions that genuinely need judgment** — with every step logged for audit
and every metric available live for management.

## 3. Reference architecture

```
                    USERS
                      |
                React Frontend  (Vite, dark theme, no UI framework)
                      |
                 FastAPI Backend (JWT auth, RBAC)
                      |
       +--------------+--------------+
       |              |              |
      RBAC        Workflow Engine   AI Layer
   (app/access.py) (SimulatedWorkflow  (AIService -> MockAIProvider)
                    Engine + recipes)
       |              |              |
       |        Business Rules       |
       |        (app/rules/*)        |
       |              |              |
       +--------------+--------------+
                      |
               Integration Layer
      (SAPIntegrationService / NonSAPIntegrationService
       -> IntegrationLog on every call)
                      |
          +-----------+-----------+
          |                       |
      SAP Adapter            Non-SAP Adapter
    (MockSAPProvider)      (MockNonSAPProvider)
          |                       |
      Mock SAP (:8100)      Mock Non-SAP (:8200)
     FastAPI microservice   FastAPI microservice
          |                       |
     +----+----+          +-------+-------+
     |    |    |          |       |       |
     MM   FI   PM       SCADA    WMS     CRM
     SD   PP   EHS      Terminal Supplier Email
                        LIMS     Documents
                           |
                      PostgreSQL (backend)
                      SQLite (mock services)
                           |
                 Audit Log / Integration Log / AI Decisions
```

Every box above is real code, not a diagram-only aspiration: workflows call
`SAPIntegrationService`, which calls `MockSAPProvider`, which makes a genuine
HTTP request to the standalone `mock-sap` FastAPI service, which reads/writes
its own database. Nothing is short-circuited or faked at the workflow layer.

## 4. Architecture diagram — provider/adapter pattern

Every external system is behind a small abstract interface, so a real
implementation can be swapped in later without touching a single workflow:

```
SAPProvider (ABC)          -> MockSAPProvider (today)      -> SAPODataProvider / SAPBTPProvider / SAPRFCProvider (future)
SCADAProvider / ... (ABC)  -> MockNonSAPProvider (today)    -> real SCADA/CRM/etc. adapters (future)
AIProvider (ABC)           -> MockAIProvider (today)         -> OpenAIProvider / AzureOpenAIProvider (future)
RPAProvider (ABC)          -> MockRPAProvider (today)        -> UiPathProvider (future)
EventBus (ABC)             -> InMemoryEventBus (today)       -> KafkaEventBus (future)
WorkflowEngine (ABC)       -> SimulatedWorkflowEngine (today) -> ProductionWorkflowEngine (future)
```

A workflow recipe (`app/workflow_engine/recipes/*.py`) only ever calls
`ctx.sap.*`, `ctx.nonsap.*`, `ctx.ai.*`, `ctx.rpa.*` — the façade classes
(`SAPIntegrationService`, `NonSAPIntegrationService`, `AIService`) — never a
provider or the mock services directly. Swapping `MockSAPProvider` for a
real SAP OData client later is a one-line change in
`app/integrations/sap/service.py`.

## 5. SAP integration strategy

`app/integrations/sap/`:
- `base.py` — `SAPProvider` ABC covering SAP MM (vendors, materials, POs,
  goods receipts, inventory, contracts), SAP FI (invoices), SAP PM
  (equipment, maintenance notifications/work orders), SAP SD (customers,
  sales orders), SAP PP (production orders), SAP EHS (incidents).
- `mock_provider.py` — `MockSAPProvider`, an `httpx` client against
  `mock-sap`'s REST API (`MOCK_SAP_BASE_URL`, default `http://127.0.0.1:8100`).
- `service.py` — `SAPIntegrationService`, the only thing workflow recipes
  call. Times every request, writes an `IntegrationLog` row (success/failure,
  latency, request/response summaries) visible on the Integration Monitor
  page, and re-raises so the workflow engine can turn a connectivity failure
  into a graceful exception instead of a hung run.

**Future**: `SAPODataProvider` (SAP Gateway/OData v2/v4), `SAPBTPProvider`
(BTP-hosted integration), `SAPRFCProvider` (direct RFC/BAPI) would each
implement `SAPProvider` against real SAP, driven by
`SAP_PROVIDER=odata|btp|rfc` and `SAP_BASE_URL`/`SAP_CLIENT_ID`/
`SAP_CLIENT_SECRET` (already present as unused placeholders in
`.env.example` — the app never requires them while `SAP_PROVIDER=mock`).

## 6. Non-SAP integration strategy

`app/integrations/nonsap/` mirrors the SAP layer exactly, with one small ABC
per subsystem (`SCADAProvider`, `TerminalProvider`, `WMSProvider`,
`CRMProvider`, `SupplierPortalProvider`, `EmailProvider`, `LIMSProvider`,
`DocumentProvider`) implemented by a single `MockNonSAPProvider` against the
standalone `mock-non-sap` service (`:8200`), and a `NonSAPIntegrationService`
façade with the same logging behavior as the SAP side.

## 7. AI architecture

`app/ai/`:
- `base.py` — `AIProvider` ABC: invoice extraction, document classification,
  vendor document extraction, HSE severity classification, maintenance alarm
  classification, production anomaly explanation, contract clause
  extraction, exception explanation.
- `mock_provider.py` — `MockAIProvider`. **Deterministic, no API key, ever.**
  Two use cases (`extract_invoice`, `classify_document`) genuinely reuse the
  repo's pre-existing Mailroom heuristics (`app/services/ocr.py`,
  `app/services/classifier.py`) rather than reimplementing them. The other
  six are new bounded-signal heuristic scorers in the same explainable style
  (every classification comes with a `reasons` list).
- `service.py` — `AIService`. Every call persists an `AIDecision` row
  (input, classification, confidence, recommendation) — the AI Decisions
  page and each run's decision trace read directly from this table.

**Hard rule, enforced by the code structure, not just convention**: an
`AIProvider` call never touches SAP and never sets a workflow's final
status. The chain is always AI → Recommendation → `app/rules/*` (deterministic)
→ Integration → SAP. A rule can (and often does) reach a different
conclusion than what the AI would have recommended alone — see
`app/rules/hse_rules.py`'s spill-volume override for an example: a Low AI
classification is still force-escalated if the spill volume alone crosses
the regulatory threshold.

**Future**: `OpenAIProvider`/`AzureOpenAIProvider` implementing the same
`AIProvider` interface, selected via `AI_PROVIDER=openai|azure` and
`OPENAI_API_KEY`/`AZURE_OPENAI_ENDPOINT` (present as unused placeholders).

## 8. RPA architecture

`app/rpa/`: `RPAProvider` ABC (login, navigate, fill_form, extract_data,
execute_transaction, interact_portal, send_email) implemented by
`MockRPAProvider`, which returns a structured trace entry
(`{action, system, status, detail, simulated_latency_ms}`) for every call
instead of driving a real browser/desktop — used for the "RPA does X" steps
in the original 15 workflow definitions (e.g. "Email PO to supplier",
"Notify technician via Teams/Email"). Future: `UiPathProvider` against the
UiPath Orchestrator API, via `RPA_PROVIDER=uipath`/`UIPATH_BASE_URL`.

## 9. Workflow architecture

`app/workflow_engine/`:
- `base.py` — `WorkflowEngine` ABC: `run(run_id, scenario=None)`.
- `simulated_engine.py` — `SimulatedWorkflowEngine`, the only implementation.
  Opens its own DB session (it runs as a FastAPI `BackgroundTasks` callable,
  outside the request's dependency-injection graph — same pattern the
  original prototype used), loads the `Workflow`/`WorkflowRun`, dispatches to
  a recipe by `workflow.key`, and finalizes the run as `Completed` or
  `Exception` based on what the recipe returns.
- `recipe_context.py` — `RecipeContext` (pre-wired `sap`/`nonsap`/`ai`/`rpa`
  services + a `record_step()` helper that keeps the live-progress UI and the
  new formal `WorkflowStep` table in sync) and `RecipeOutcome`.
- `recipes/*.py` — one function per workflow. **9 of the 15 workflows get
  rich, bespoke, multi-record business logic** (the ones exercised by the
  acceptance-criteria walkthrough and the golden demo scenarios):
  `PO_CREATE`, `INV_MATCH`, `VENDOR_ONBOARD`, `MAINT_WO`, `HSE_INCIDENT`,
  `CONTRACT_EXPIRY`, `CRUDE_RECON`, `PROD_REPORT`, `SALES_ORDER`. The
  remaining 6 (`SPARE_REPLEN`, `SHIFT_HANDOVER`, `EXPENSE_PROC`,
  `FUEL_RECON`, `COMPLIANCE_DOC`, `ENV_COMPLIANCE`) still call real mock
  endpoints per step and apply a genuine rule, just with less multi-record
  reconciliation depth — a deliberate scope decision, not a shortcut that
  silently randomizes outcomes. `generic_fallback.py` is a safety net for any
  future workflow key without a registered recipe.
- **No `random.random()` anywhere in the outcome path.** Every Completed vs.
  Exception decision traces back to a real data comparison run through
  `app/rules/*`.

**Future**: `ProductionWorkflowEngine` implementing the same `WorkflowEngine`
interface against a real BPM/orchestration system — the router that triggers
runs (`app/routers/runs.py`) never changes.

## 10. RBAC

Unchanged from the original prototype (`app/access.py` remains the single
source of truth):

| Level | Scope |
|---|---|
| **Manager** | Runs only explicitly granted workflows. Sees only their own runs/exceptions, plus can Retry/Escalate/Request-correction on their own exceptions. |
| **Senior Manager** | Full department visibility of workflows/runs/exceptions. Can Approve/Reject exceptions. |
| **Department Head** | Everything Senior Manager can, plus manages department users and workflow access grants. |
| **Admin** | Cross-department, everything. |

New pages (Integration Monitor, AI Decisions, Audit Log, Analytics, Demo
Scenarios) are gated at Senior Manager+, matching the existing Access
Management gate. System Health is open to any authenticated user (it exposes
no department-scoped data). Exception actions are gated per-action by
`app/rules/authorization_rules.py` on top of the existing department
visibility check — a Manager can Retry/Escalate/Request-correction on their
own exceptions but cannot Approve/Reject, even their own.

## 11. Synthetic data — PetroNova Energy Corporation

A fully fictional company, generated deterministically (fixed seed `42`,
`Faker` + `random`) so every fresh reseed produces byte-identical data,
including the golden demo-scenario fixtures. Volumes match the platform
spec: 500+ vendors, 1000+ materials, 300+ customers, 500+ equipment, 500+
contracts, 2000+ purchase orders, 2000+ goods receipts, 3000+ invoices,
1500+ maintenance orders, 2000+ sales orders, 5000+ production records, 500+
HSE incidents, 2000+ expenses, 10000+ SCADA telemetry readings — generated
in a few seconds via bulk two-phase inserts
(`mock-systems/*/app/seed/generate_synthetic_data.py`). Records are
relationally consistent (a `PurchaseOrderItem` always references a real
`Material`; a `GoodsReceiptItem` always references a real
`PurchaseOrderItem`), not independently random rows.

## 12. Mock SAP (`mock-systems/mock-sap/`)

A standalone FastAPI service (port `8100`, own SQLite DB by default) exposing
SAP-shaped REST endpoints — not a byte-for-byte SAP API clone, but realistic
enough to demonstrate the integration pattern:

```
GET  /api/mm/vendors                    GET  /api/mm/vendors/{vendor_code}
POST /api/mm/vendors
GET  /api/mm/materials                  GET  /api/mm/materials/{material_code}
GET  /api/mm/purchase-orders            GET  /api/mm/purchase-orders/{po_number}
POST /api/mm/purchase-orders
GET  /api/mm/goods-receipts/{po_number}
GET  /api/mm/inventory/{material_code}
GET  /api/mm/contracts                  GET  /api/mm/contracts/{contract_number}
GET  /api/fi/invoices/{invoice_number}  POST /api/fi/invoices
GET  /api/pm/equipment/{equipment_id}
POST /api/pm/notifications              POST /api/pm/work-orders
GET  /api/sd/customers/{customer_code}  POST /api/sd/sales-orders
GET  /api/pp/production-orders
POST /api/ehs/incidents
GET  /api/health
```

## 13. Mock Non-SAP (`mock-systems/mock-non-sap/`)

Standalone FastAPI service (port `8200`, own SQLite DB by default):

```
GET  /api/scada/equipment/{equipment_id}/telemetry
GET  /api/scada/alarms
GET  /api/terminal/receipts             GET  /api/terminal/tank-readings
GET  /api/wms/inventory
GET  /api/crm/customers                 GET  /api/crm/orders
GET  /api/supplier/documents            POST /api/supplier/onboarding
GET  /api/email/inbox                   POST /api/email/send
GET  /api/lims/test-results
GET  /api/documents/{document_id}
GET  /api/health
```

Entities reference mock-sap records by business key (`equipment_id`,
`vendor_code`, `po_number`, ...), never by internal row id — exactly how a
real non-SAP system would only know SAP's business keys, not its database
internals. CRM customers are a deliberately separate dataset from SAP SD
customers (realistic — most orgs run both with some drift), and the
Email endpoints here are a separate, generic company inbox — not a
repurposing of the existing Mailroom feature, which stays a dedicated,
already-tested AP-invoice-triage flow.

## 14. Golden demo scenarios

Deterministic, reproducible on demand via the **Demo Scenarios** page —
every one executes through the real `SimulatedWorkflowEngine`, not a
separate fake demo path:

| Category | Scenario | Result |
|---|---|---|
| Invoice | PO=100, GRN=100, Invoice=100, same price | `AUTO_APPROVE` |
| Invoice | PO=100, GRN=95, Invoice=100 | `QUANTITY_MISMATCH` |
| Invoice | PO price 125,000 vs. invoice price 140,000 | `PRICE_MISMATCH` |
| Invoice | Same invoice number resubmitted | `DUPLICATE_INVOICE` |
| Invoice | Invoice exists, GRN doesn't | `MISSING_GRN` |
| Maintenance | Pump vibration 12.0 vs. threshold 5.0 (2.4x) | SCADA alarm → `EquipmentAlarmEvent` on the `EventBus` → AI `Emergency` classification → SAP PM notification + work order |
| Crude | Terminal 9,950 bbl / Tank 9,850 bbl vs. SAP 10,000 bbl receipt | `HARD_EXCEPTION` (>0.5% variance) |
| Vendor | Insurance certificate expired 15 days ago | `EXPIRED_INSURANCE` exception |
| HSE | "Fire reported... extinguished quickly, no injuries" | AI classifies `Critical` → auto-escalates |
| Contract | Expires in 12 days, owned | `RENEWAL_REVIEW` |
| Production | Planned 10,000 bbl, actual 8,500 bbl (15% under) | `CRITICAL_ANOMALY` |

## 15. Database

`app/models.py` (unchanged): `User`, `AuditLog`, `Workflow`,
`WorkflowAccess`, `WorkflowRun`, `ExceptionItem`, plus the pre-existing
Mailroom tables (`MailMessage`, `MailAttachment`, `InvoiceExtraction`).

`app/models_platform.py` (new, additive only): `IntegrationLog`,
`AIDecision`, `Event`, `WorkflowStep` (formal per-step rows, alongside — not
replacing — the existing `WorkflowRun.log_json` the UI already renders),
`ExceptionAction`.

Main backend runs on **PostgreSQL** by default in Docker (SQLite remains the
local-dev default via `DATABASE_URL`, same driver-agnostic
`create_engine()` as before — nothing SQLite-specific except one
`connect_args` branch). `mock-sap`/`mock-non-sap` default to their own
SQLite files (simpler for two read-mostly reference services; swappable to
Postgres via the same `DATABASE_URL` pattern if ever needed). Alembic
migrations are real (autogenerated from `SQLModel.metadata`, not the
original empty stub) — see `backend/alembic/versions/`.

Deliberate deviation: no separate `roles` table. The existing `Level` enum +
`app/access.py` already is RBAC's single source of truth; a parallel table
would fragment that without adding anything.

## 16. API architecture

```
/api/auth/*           login, logout, me
/api/workflows/*       list, dashboard, {id} detail
/api/runs/*             trigger, list, {id} detail (accepts ?scenario=)
/api/exceptions/*        list, {id} detail (full trace), {id}/action, {id}/resolve
/api/admin/*               users, workflow access grants, audit-log
/api/mailroom/*              (pre-existing, unchanged)
/api/knowledge/*               (pre-existing, unchanged)
/api/integrations/*             status, logs   (Senior Manager+)
/api/ai/decisions                              (Senior Manager+)
/api/analytics/dashboard                        (Senior Manager+)
/api/demo/scenarios, /scenarios/{id}/run        (Senior Manager+)
/api/system/health                              (any authenticated user)
```

Mock systems are entirely separate services, not proxied under the main
API: `mock-sap` on `:8100`, `mock-non-sap` on `:8200`.

## 17. Security

Unchanged and still enforced: bcrypt password hashing, JWT (HS256), login
lockout (5 attempts → 15 min), CORS from settings, security headers
middleware, `APP_ENV=production` fails fast on the default secret key.
Nothing new required a change here — the new routers reuse the exact same
`get_current_user`/`require_min_level` dependencies as the original ones.

## 18. Audit

`app/audit.py` (`log_action()`) is now the single shared helper — previously
a private function duplicated only inside `admin.py`. New call sites:
`auth.login`/`auth.logout`, `workflow.execution_started/completed/failed`,
`exception.created`, `exception.resolved`/`approve`/`reject`/`retry`/
`escalate`/`request_correction`, on top of the original `user.created`/
`user.updated`/`workflow_access.updated`. `GET /api/admin/audit-log`'s
department-scoping now recognizes `WorkflowRun` and `ExceptionItem` target
types, not just `User`.

## 19. Observability

Unchanged: `RequestIDMiddleware` (correlation via `X-Request-ID`),
structured JSON-ish logging. New: every workflow run carries a
`correlation_id` (`run-{id}-{uuid}`) threaded through every
`SAPIntegrationService`/`NonSAPIntegrationService`/`AIService` call it makes,
so `IntegrationLog`/`AIDecision` rows for one run are all findable by that
id — the full chain (Workflow → Step → AI → Rules → SAP → DB → Audit) is
traceable end-to-end from a single run.

## 20. Local installation (without Docker)

Requires Python 3.12 and Node 18+.

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Mock SAP (separate terminal)
cd mock-systems/mock-sap
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8100

# Mock Non-SAP (separate terminal)
cd mock-systems/mock-non-sap
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8200

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Each service seeds its own database
automatically on first startup (idempotent — only seeds if empty).

To reset everything back to the golden-scenario baseline:
```bash
backend\.venv\Scripts\python.exe scripts\seed_demo.py --scale full
```
(Restart the three services afterward — this reseeds their databases
directly and stops short of restarting the running process for you.)

### System dependency: Tesseract OCR (Mailroom feature only)

The Mailroom feature's OCR is real. Install via
`winget install --id UB-Mannheim.TesseractOCR` for local dev; the Docker
backend image installs it automatically.

## 21. Docker setup

```bash
docker compose up --build
```

Brings up `postgres`, `mock-sap` (`:8100`), `mock-non-sap` (`:8200`),
`backend` (`:8000`, connected to Postgres), and `frontend` (`:8080`, nginx
serving the built SPA and reverse-proxying `/api` to `backend`). Open
`http://localhost:8080`. No `.env` file is required — every variable in
`.env.example` has a working default already in `docker-compose.yml`.

Redis/Kafka/Kubernetes are intentionally not part of this compose file —
nothing in this design needs a cache or message broker yet (see §24).

Deploying this somewhere real (not just local demo)? See **[PRODUCTION.md](PRODUCTION.md)**
for the hardening checklist — TLS, secrets, rate limiting, backups, and what's
deliberately still out of scope.

## 22. Demo accounts

All demo accounts use password **`Demo@123`** (unchanged from the original
prototype):

| Username | Department | Level |
|---|---|---|
| `admin` | — | Admin |
| `asha.rao` / `vikram.shah` / `neha.kapoor` | Procurement | Manager / Senior Manager / Dept Head |
| `rahul.verma` / `priya.nair` / `suresh.iyer` | Maintenance | Manager / Senior Manager / Dept Head |
| `anjali.mehta` / `karan.singh` / `deepa.joshi` | Finance | Manager / Senior Manager / Dept Head |
| `farhan.ali` / `meera.pillai` / `omar.hassan` | HSE | Manager / Senior Manager / Dept Head |
| `sanjay.gupta` / `leela.menon` / `arjun.reddy` | Production | Manager / Senior Manager / Dept Head |

## 23. Demo walkthroughs

1. Log in as `admin` → Dashboard shows all 9 departments, 15 workflows.
2. **Demo Scenarios** → Invoice → run all 5 variants → each lands on
   `/runs/{id}` with live step-by-step progress against real mock-sap data.
3. Open the resulting exception from **Exception Queue** → full trace: AI
   explanation, evidence (every step's real SAP response), related SAP/
   non-SAP records, audit history → click **Approve**/**Escalate**/etc.
4. **Demo Scenarios** → Maintenance → watch SCADA alarm → AI classification
   → SAP PM notification/work order, then check **Integration Monitor** for
   the live call stats and **AI Decisions** for the classification trace.
5. **Analytics** → real automation rate / hours-saved numbers, computed from
   the runs you just triggered — never hardcoded.
6. **Audit Log** → every action above, attributed and timestamped.
7. Log in as `neha.kapoor` (Procurement Dept Head) → **Access Management** →
   grant `asha.rao` (Manager) the third Procurement workflow → log in as
   `asha.rao` → see it unlocked on her Dashboard.
8. Log in as `farhan.ali` (HSE Manager) → confirm Analytics/Integration
   Monitor/Demo Scenarios/Audit Log are inaccessible (Senior Manager+ only) —
   department isolation and level gating both hold.

## 24. Future production architecture

None of the following require changing a single workflow recipe — only the
provider implementation each façade resolves to:

| Demo (today) | Production (future) |
|---|---|
| `MockSAPProvider` | `SAPODataProvider` / `SAPBTPProvider` / `SAPRFCProvider` |
| `MockAIProvider` | `OpenAIProvider` / `AzureOpenAIProvider` / private LLM |
| `MockRPAProvider` | `UiPathProvider` |
| `InMemoryEventBus` | `KafkaEventBus` |
| SQLite (mock services) / dev-default SQLite (backend) | Postgres everywhere, managed (RDS/Cloud SQL) |
| JWT username/password | Enterprise SSO/OIDC/SAML |
| Manual `IntegrationLog`/structured logs | OpenTelemetry + enterprise observability stack |
| `docker compose` | Kubernetes / managed container platform |

## Project layout

```
backend/                    Main FastAPI app (auth, RBAC, workflow engine, rules, AI/RPA/event-bus providers)
  app/
    integrations/sap/, nonsap/    Provider ABCs + Mock implementations + IntegrationService façades
    ai/, rpa/, events/             AIProvider/RPAProvider/EventBus + Mock implementations
    rules/                          Business Rules Engine (8 modules, KB-sourced thresholds)
    workflow_engine/                 SimulatedWorkflowEngine + 15 recipes
    routers/                          auth, workflows, runs, exceptions, admin, mailroom, knowledge,
                                       integrations, ai, analytics, demo, system
  tests/                              97 tests (pytest)
  alembic/                            Real migrations
mock-systems/
  mock-sap/                          SAP MM/FI/PM/SD/PP/EHS REST API + synthetic data generator (21 tests)
  mock-non-sap/                      SCADA/Terminal/WMS/CRM/Supplier/Email/LIMS/Documents (9 tests)
frontend/
  src/pages/                         Dashboard, RunDetail, WorkflowDetail, Exceptions, ExceptionDetail,
                                      Mailroom, Admin, IntegrationMonitor, AIDecisions, AuditLog,
                                      DemoScenarios, Analytics, SystemHealth
scripts/
  seed_demo.py                       Full reset+reseed orchestrator across all three services
  generate_documents.py              Synthetic PDF documents (invoices/vendor/contracts/orders/expenses/hse)
data/documents/                      Generated PDFs (gitignored)
docker-compose.yml
```

## Known limitations

- Mock services default to SQLite, not Postgres (documented decision, §15).
- 6 of 15 workflows use a lighter "generic-but-real" recipe rather than
  bespoke multi-record reconciliation logic (documented decision, §9).
- `invoice_generator.py`'s PIL-rendered PNGs fall back to a basic default
  font on Linux/Docker (no `arial.ttf` there) — cosmetic only.
- No MFA, token revocation/refresh tokens, or frontend test coverage — out
  of scope for this demo, same as the original prototype.
- Redis/Kafka/Kubernetes are not part of this build — nothing here needs a
  cache or broker yet; see §24 for where Kafka would slot in later.
