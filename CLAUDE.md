# CLAUDE.md

Context for Claude Code (or any agent) working in this repository.

## What this is

**RPA/SAP Ops Console — Oil & Gas Demo.** A prototype RPA console for
middle-management, sitting across SAP and non-SAP applications. Managers
trigger and monitor automated workflows; exceptions land in a review queue;
access is scoped per department and per management level. SAP/SCADA/portals
are **simulated** — there are no live external system connections.

- **Backend**: FastAPI + SQLModel, JWT auth, bcrypt hashing. SQLite by
  default, `DATABASE_URL`-driven so Postgres works via env var alone.
- **Frontend**: React + TypeScript + Vite, hand-built dark theme, no UI
  framework.
- **Access model**: Manager → Senior Manager → Department Head → Admin,
  scoped by department (`app/access.py` is the single source of truth for
  permission checks).

## Departments

Procurement, Maintenance, Finance, HSE, Production, Material Management,
Warehouse Management, Sales & Distribution, Supply Chain Management (+ Admin,
cross-department only). Each of the original 5 has 3 seeded RPA workflows
(15 total) in `backend/app/seed_data.py`.

## Project layout

```
backend/
  app/
    main.py              FastAPI app, middleware, startup seeding
    config.py             pydantic-settings: SECRET_KEY, DATABASE_URL,
                           ALLOWED_ORIGINS, APP_ENV — fails fast if
                           APP_ENV=production with the default secret
    models.py              SQLModel tables (User, Workflow, WorkflowAccess,
                            WorkflowRun, ExceptionItem, AuditLog,
                            MailMessage, MailAttachment, InvoiceExtraction)
    access.py               RBAC helpers (single source of truth)
    auth.py / deps.py        JWT issuing/verification, auth dependencies
    middleware.py             Request-ID logging + security headers
    logging_config.py          Structured (JSON-ish) logging setup
    database.py                DATABASE_URL-driven engine
    seed_data.py                Demo users + 15 workflow definitions
    seed_data_mailroom.py        15 mock emails, 5 with invoice attachments
    knowledge_base/                Markdown rules/SOPs, one per department
    services/
      classifier.py                Heuristic "is this an invoice email?"
                                    scorer (see below)
      ocr.py                        Tesseract OCR + regex field extraction
      invoice_generator.py           Renders the 5 invoice PNGs with PIL
    routers/                        auth, workflows, runs, exceptions,
                                     admin, mailroom, knowledge
  tests/                             pytest suite (17 tests) — auth, RBAC,
                                     workflow lifecycle, mailroom
  alembic/                           Migrations (initial schema generated
                                     from SQLModel.metadata)
frontend/
  src/
    api.ts                Typed fetch wrapper for the backend
    auth/AuthContext.tsx
    pages/                  Login, Dashboard, RunDetail, Exceptions, Admin,
                             Mailroom
    components/              Layout (sidebar/topbar), RunStatusBadge
  vite.config.ts              Dev server; proxies /api to the backend.
                               Configurable via env: VITE_API_PROXY_TARGET
                               (default http://127.0.0.1:8000), PORT
                               (default 5173)
```

## Demo accounts

All demo accounts use password **`Demo@123`**. `admin` is cross-department
Admin. Each department has a Manager/Senior Manager/Department Head trio
(see README.md for the full username list) — e.g. Procurement:
`asha.rao` (Manager), `vikram.shah` (Senior Manager), `neha.kapoor` (Dept
Head). Maintenance Manager is `rahul.verma`.

## Running locally

Backend:
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
SQLite DB is created and seeded automatically on startup (users, workflows,
and the mailroom inbox). For a from-scratch schema instead of `create_all`,
run `alembic upgrade head`.

Frontend:
```bash
cd frontend
npm install
npm run dev
```
Default: http://localhost:5173, proxying `/api` to `http://127.0.0.1:8000`.
To run against a backend on a different port (e.g. when another backend
instance already owns 8000), override the proxy target and/or the dev
server's own port:
```bash
VITE_API_PROXY_TARGET="http://127.0.0.1:8010" PORT=5180 npm run dev
```

### System dependency: Tesseract OCR

The mailroom feature's OCR is real, not simulated — it requires the
Tesseract binary on PATH (or at the default Windows install location
`C:\Program Files\Tesseract-OCR\tesseract.exe`, which `app/services/ocr.py`
falls back to). Install via `winget install --id UB-Mannheim.TesseractOCR`.

### Known environment gotcha

`sqlmodel==0.0.22` (pinned in `requirements.txt`) breaks on Python 3.14 +
pydantic 2.13 (`PydanticUserError: Field 'id' requires a type annotation`).
Fix: `pip install -U sqlmodel` in the venv (tested working at 0.0.39). Not
worth re-pinning requirements.txt since it depends on the local Python
version; just remember to do this after a fresh `pip install -r
requirements.txt` on newer Python.

## Feature: Mailroom (invoice triage + OCR)

Added to prove out an "AI reads email, OCR reads invoices" pipeline before
committing to a real email/OCR integration.

- **Knowledge base** (`GET /api/knowledge`, `GET /api/knowledge/{dept}`):
  markdown rules/SOPs per department — 3-way match tolerances, HSE incident
  reporting windows, warehouse cycle-count rules, credit-hold policy, vendor
  lead-time SLAs, etc. Written as real reference material, not filler.
- **Mock inbox** (`seed_data_mailroom.py`): 15 emails seeded on startup.
  5 are genuine vendor invoice submissions with a real rendered PNG
  attachment (`services/invoice_generator.py`, via PIL — letterhead, invoice
  #, PO #, line items, subtotal/tax/**TOTAL DUE**). The other 10 are
  deliberately similar-looking noise (an HSE spill email mentioning an
  "amount spilled", a PO follow-up with no invoice yet, a newsletter, a
  month-end accrual reminder) so the classifier has to actually discriminate
  rather than keyword-match "invoice".
- **Classifier** (`services/classifier.py`): transparent heuristic scorer
  (no LLM API key available in this environment, so this stands in for one)
  — signals: attachment presence/filename shape, invoice-number/PO-number
  regex hits in subject/body, currency amounts, sender heuristics
  (accounts@/billing@ vs noreply@/newsletter@), and — the strongest signal —
  whether OCR of the attachment actually contains invoice-shaped text.
  Confidence threshold 0.6. Every contributing signal is recorded as a
  human-readable reason string for auditability.
- **OCR** (`services/ocr.py`): `pytesseract.image_to_string` on the
  attachment, then regex extraction of vendor name, invoice number, PO
  number, date, total amount + currency. **Known-fixed bug**: the total-
  amount regex originally matched "Subtotal" (substring "total"), returning
  the wrong figure; fixed with a negative lookbehind `(?<!sub)` so it only
  matches standalone "Total"/"Total Due"/"Grand Total".
- **API** (`routers/mailroom.py`): `GET /messages`, `GET /messages/{id}`,
  `POST /messages/{id}/classify`, `POST /classify-all` (runs classification
  across all 15 and returns the flagged count + full results),
  `GET /attachments/{id}/file` (serves the raw invoice image).
- **Frontend** (`pages/Mailroom.tsx`): lists the 15-email inbox, a "Run AI
  triage" button hitting `classify-all`, tags each email with verdict +
  confidence, and an expandable detail panel for flagged ones showing the
  extracted OCR fields.

**Verified result** (real run, not simulated): of the 15 seeded emails,
exactly the 5 real invoices are flagged, each with correct vendor name,
invoice number, PO number, and total amount matching the source document
pixel-for-pixel (i.e., genuinely OCR'd, not hardcoded). All 10 non-invoice
emails — including the tricky ones — score near 0.0–0.04, well under the
0.6 threshold.

## Production hardening done (Docker/CI explicitly out of scope)

- **Config**: `app/config.py`, `.env.example`. `APP_ENV=production` refuses
  to boot with the default `RPA_SAP_SECRET_KEY`.
- **Security**: login lockout (5 attempts → 15 min), CORS origins from
  settings, security headers middleware (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, HSTS outside dev), `AuditLog` table +
  writes on admin user/access changes, readable via
  `GET /api/admin/audit-log`.
- **Data layer**: `DATABASE_URL`-driven engine (swap to Postgres via env
  var alone), Alembic migrations (`alembic upgrade head` is the real
  production path; `create_all` remains as a zero-friction dev fallback).
- **Tests**: `backend/tests/`, 17 tests, pytest. Run with
  `.venv\Scripts\python -m pytest -q` from `backend/`.
- **Observability**: structured JSON-ish logging
  (`app/logging_config.py`), request-ID middleware, `/api/health` now also
  checks DB connectivity (`{"status": "ok", "db": "ok"}`).

**Still open** (deliberately out of scope per the user's instruction, or
noted as future work): Docker/docker-compose, CI/CD pipeline, a real
Postgres instance actually stood up (the app supports it, but this dev
environment only exercises SQLite), MFA, token revocation/refresh tokens,
frontend test coverage.

## Working conventions in this repo

- `app/access.py` is the single source of truth for RBAC — never duplicate
  permission logic in a router.
- Background work (workflow run simulation) opens its own
  `Session(engine)` directly rather than using the `get_session` FastAPI
  dependency, because it isn't running inside a request. **If you add
  tests for anything that spawns a background task, you must also point
  the module's `engine` at the test engine** (see
  `tests/conftest.py`: `runs_module.engine = TEST_ENGINE`) or the
  background task will silently operate on a different (empty) database.
- Generated files (invoice PNGs, the SQLite DB) are gitignored and
  regenerate automatically on startup — never commit them.
- This repo is normally worked in a git worktree
  (`.claude/worktrees/...`); the `.venv` is untracked and per-worktree —
  don't assume a sibling worktree's venv is usable here.
