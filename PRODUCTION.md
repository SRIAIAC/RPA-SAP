# Production hardening checklist

This document is for deploying this repo as a real, always-on internal tool
running on **mock/synthetic data** (no real SAP, AI, or UiPath credentials).
That's a deliberate scope: see "What this checklist does NOT cover" at the
bottom for what's needed before this can touch real SAP/company data — none
of it is code work, it's credentials and decisions only your organization
can provide.

If you haven't read them yet: README.md §17 (Security) and §24 (Future
production architecture) cover what's already true architecturally. This
file is the operational checklist for standing the container stack up
somewhere real.

## 1. Before you deploy — required config changes

The demo defaults in `.env.example`/`backend/.env.example` are intentionally
insecure so `docker compose up` works with zero setup. Every item below is
enforced or at least warned about at backend startup once `APP_ENV=production`
(see `backend/app/config.py`), but check them explicitly before going live:

- [ ] **`APP_ENV=production`** in your root `.env`. This alone flips on HSTS
      headers and the fail-fast checks below.
- [ ] **`RPA_SAP_SECRET_KEY`** — generate with:
      ```
      python scripts/generate_secret_key.py
      ```
      The backend refuses to start with the default value once
      `APP_ENV=production`.
- [ ] **`POSTGRES_PASSWORD`** — override the `rpa_sap` default. The backend
      refuses to start if `DATABASE_URL` still contains the default
      `rpa_sap:rpa_sap@` pair while `APP_ENV=production`.
- [ ] **`ALLOWED_ORIGINS`** — set to your real frontend origin(s), e.g.
      `https://ops.example.com`. Left at the localhost default, the backend
      logs a warning at startup and the browser will hard-fail every request
      with a CORS error.
- [ ] **`RATE_LIMIT_PER_MINUTE`** — default `120`/client IP is a reasonable
      starting point for an internal tool; raise it if a shared NAT/proxy
      means many real users share one IP, lower it if you want it tighter.
- [ ] Store the resulting `.env` outside version control (it already is,
      via `.gitignore`) and outside any shared/synced folder. For anything
      beyond a single-box deployment, put these in your platform's secrets
      manager instead of a `.env` file — see §6.

## 2. Deploying

```bash
git pull
docker compose up -d --build
```

This brings up `postgres`, `mock-sap`, `mock-non-sap`, `backend`, `frontend`
— unchanged from the demo path, just with your production `.env` values in
effect. Confirm everything is healthy:

```bash
docker compose ps
curl http://localhost:8000/api/health
```

### With TLS (recommended for anything beyond localhost)

A `caddy` service is defined behind the `tls` Compose profile — not part of
the default `docker compose up` so the offline demo path never needs ports
80/443 or a domain. Enable it with:

```bash
docker compose --profile tls up -d --build
```

`DOMAIN` (root `.env`, default `localhost`) controls the certificate:
- Left at `localhost` (or any non-public hostname): Caddy issues a
  locally-trusted self-signed certificate automatically — no DNS or public
  IP needed. Fine for a pure-internal/on-prem deployment reached by IP or
  an internal DNS name.
- Set to a real, publicly-resolvable hostname with ports 80/443 reachable
  from the internet: Caddy obtains a real Let's Encrypt certificate via
  ACME automatically, no extra config.

Point users at `https://<DOMAIN>` instead of `http://localhost:8080`
once this is enabled.

## 3. What's already hardened (done in this pass)

- **Container hygiene**: `restart: unless-stopped`, healthchecks, and
  per-service CPU/memory limits on every service (`docker-compose.yml`).
- **Non-root containers**: `backend`, `mock-sap`, `mock-non-sap` all run as
  an unprivileged `appuser` (uid 1000), not root. `frontend`'s nginx is
  deliberately left as-is — its worker processes already drop privileges
  automatically, which is the standard nginx security posture.
- **Rate limiting**: `RateLimitMiddleware` (`backend/app/middleware.py`)
  enforces a per-client-IP sliding window on every endpoint except health
  checks, on top of the pre-existing login-lockout mechanism (5 failed
  attempts → 15 min). In-memory/single-process by design — see the
  docstring in that file for what changes if the backend is ever scaled to
  multiple instances (would need a shared store).
- **Config fail-fasts**: default secret key and default DB credentials both
  refuse to boot under `APP_ENV=production` (§1 above).
- **TLS**: optional Caddy reverse proxy, §2 above.
- **Backups**: §4 below.
- Everything from before this pass: bcrypt password hashing, JWT (HS256),
  RBAC (`app/access.py`), CORS allowlist, security headers middleware,
  full audit log (`app/audit.py`), request-ID correlation across every
  workflow step/AI decision/integration call (README §19).

## 4. Backups

Only the `postgres` service holds state worth preserving — it's the system
of record for users, workflow runs, exceptions, and the audit log.
`mock-sap`/`mock-non-sap` are SQLite-backed and reseed synthetic data on
every startup by design, so they're intentionally excluded.

**Back up:**
```bash
python scripts/backup_postgres.py            # writes ./backups/rpa_sap_<timestamp>.dump
python scripts/backup_postgres.py --keep 30   # override retention (default: keep last 14)
```

**Restore** (destructive — drops and recreates every object in the target
database first; dry-runs by default):
```bash
python scripts/restore_postgres.py backups/rpa_sap_20260101_030000.dump          # prints what it would do
python scripts/restore_postgres.py backups/rpa_sap_20260101_030000.dump --yes    # actually restores
```

Both scripts shell out to `docker compose exec postgres pg_dump`/`pg_restore`
and were verified end-to-end against a live container while writing this
checklist.

**Scheduling**: neither script sets up its own scheduler — wire one up on
whatever host runs `docker compose`:
- Linux: a cron entry, e.g. `0 3 * * * cd /path/to/repo && /path/to/python scripts/backup_postgres.py >> backups/backup.log 2>&1`
- Windows: a Task Scheduler task running the same command daily.

`backups/` is gitignored — dumps may contain real user/audit data once this
is handling anything beyond the demo, so treat the directory itself as
sensitive and back it up off-box (S3, another disk, etc.) rather than
relying on it living only on the app server.

## 5. Post-deploy verification

- [ ] `docker compose ps` — all services `healthy`.
- [ ] Log in through the real URL (not localhost) as `admin` / `Demo@123`,
      then **change or retire that password** — see §6, it's a real gap.
- [ ] Trigger one workflow run end-to-end (README §23, step 2) and confirm
      it completes and shows up in Audit Log.
- [ ] Confirm `/api/health` and (if using TLS) `https://<DOMAIN>` both
      resolve as expected from a machine other than the one running Docker.
- [ ] Take a first backup (`scripts/backup_postgres.py`) and confirm the
      restore dry-run output looks right.

## 6. What this checklist does NOT cover

These are real gaps for a genuine production deployment, deliberately left
alone because closing them requires decisions or credentials that belong to
you/your organization, not code changes I can make unilaterally:

- **Real SAP/AI/RPA integration.** Every workflow currently runs against
  `MockSAPProvider`/`MockAIProvider`/`MockRPAProvider`. Swapping to real
  ones is a provider-implementation task, not a workflow rewrite — see
  README §24's table — but it needs your actual SAP OData/RFC credentials,
  an OpenAI/Azure OpenAI API key, and a UiPath Orchestrator endpoint, none
  of which exist in this environment.
- **Real company data.** This platform only knows the synthetic "PetroNova
  Energy Corporation" dataset. Loading real vendor/material/financial data
  is a data-migration project (source system exports, mapping, validation,
  probably a real ETL step) that needs your data governance process, not a
  script I can write blind.
- **Demo account passwords/rotation.** All demo users share `Demo@123`
  today. Before real users touch this, replace the seeded accounts with
  real ones (or wire up SSO/OIDC — README §24) and force a password change
  on first login; there's no forced-rotation or MFA mechanism yet.
- **Secrets manager.** `.env`-file secrets are fine for a single box; for
  anything with more than one operator or a real deployment pipeline, move
  `RPA_SAP_SECRET_KEY`/`POSTGRES_PASSWORD` into your cloud provider's
  secrets manager (or Vault) and inject them at container-start time
  instead of committing them to a file on disk anywhere.
- **Centralized logging/alerting.** Structured JSON-ish logs and
  request-ID correlation exist (README §19), but nothing ships them
  anywhere or pages anyone. Wiring `docker compose logs` (or the
  containers' stdout) into an actual log aggregator + alerting on
  container restarts/health failures is infra work specific to wherever
  this ends up running.
- **DNS, domain, and hosting decisions.** The Caddy service (§2) handles
  TLS once you have a domain/host; picking that domain, cloud provider,
  and network setup (VPN-only vs. public, firewall rules) is your call.
- **Horizontal scaling.** The rate limiter and in-memory event bus are
  explicitly single-process (see their docstrings). If this ever needs to
  run as more than one backend replica, both need a shared backing store
  first — not needed at current expected internal-tool traffic levels.
