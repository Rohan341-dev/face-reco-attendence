# FaceTrack AI — Architecture & Incremental Implementation Plan

Status: living document. Each phase must leave the application runnable and its
automated tests green before the next phase begins.

## 1. Current state (as inspected)

Implemented and tested:

- Django 5 / DRF backend with JWT auth + TOTP MFA (`apps/accounts`).
- Tenant registry, onboarding, branches, departments, memberships, RBAC
  (`apps/tenants`, `apps/core/permissions.py`).
- PostgreSQL Row-Level Security via transaction-local GUCs
  (`apps/core/rls.py`, `apps/core/middleware.py`, RLS migrations).
- People, consent (append-only), encrypted biometric templates (`apps/people`).
- Shifts, schedules, holidays, leave requests (`apps/schedules`).
- Central attendance engine (`apps/attendance/engine.py`): eligibility,
  idempotency, dedupe window, overnight shifts, daily record rebuild.
- AES-256-GCM secret encryption (`apps/core/crypto.py`), audit log, error
  envelope, pagination.
- OpenAPI schema generation + TS type codegen pipeline.

Gaps that block a working product (ordered by priority):

1. `attendance` and `devices` apps have models but **no migrations**, which also
   breaks test DB creation (`sync_apps` creates their FK tables before tenant
   tables exist). Their tables have no RLS policies.
2. No HTTP API for attendance or devices; no WebSocket consumers; no Celery
   app despite broker config; `token_blacklist` used but not installed.
3. `CorrectionRecord` exists but no `apply_correction()` path.
4. Web / mobile / terminal are empty scaffolds (no UI code); web's entry point
   `src/main.tsx` is missing.
5. AI service is only a `requirements.txt`; no pipeline, no evaluation report.
6. No Dockerfiles, nginx/Prometheus config, seed data, CI/CD, or module docs.
7. `make run-ai` points at a non-existent venv path.

## 2. Target architecture

```
Clients
  web (React 19)      mobile (Expo)      terminal (kiosk)
        \                  |                   /
         \-----------------+------------------/
                    HTTPS / JWT
                           |
              Nginx (TLS termination)
                           |
        +------------------+-------------------+
        |                                      |
   Django (DRF)                          FastAPI (AI)
   - auth/MFA, tenancy, RBAC             - capture auth
   - people/consent/biometrics           - detection + quality
   - schedules/leave/holidays            - liveness
   - attendance engine (ONLY writer)     - embeddings + verify
   - devices/pairing/sync                - no covert ID, no retention
   - corrections/audit/reports
        |         |            |
   PostgreSQL   Redis       Celery
   (RLS +       (cache,    (tasks, retries)
    pgvector)    channels)
```

Invariant: every attendance signal — regardless of channel — enters through
`apps.attendance.engine.process_event()`. Detection or recognition alone never
authorizes attendance: consent, liveness, verification status, device
authorization and eligibility are enforced in the engine.

## 3. Tenant isolation model

- `TenantContextMiddleware` resolves `org_id` from the JWT claim (header is
  only a fallback), verifies an active `Membership`, and pins GUCs:
  `app.current_user`, `app.platform_admin`, `app.current_tenant`.
- Every request runs in `transaction.atomic()` so `SET LOCAL` scopes all ORM
  and raw SQL.
- Every tenant table has `ENABLE + FORCE ROW LEVEL SECURITY` with a policy keyed
  on `organization_id = app.current_tenant`, plus a platform-admin escape hatch
  that is always audit-logged.
- Views additionally filter `organization_id=request.organization_id` and
  enforce role permissions — RLS is defence in depth, not the only layer.
- Celery tasks and WebSocket consumers pin the same GUCs before touching data.

## 4. Data model summary

Tenant-scoped: Organization (registry), Branch, Department, Membership,
OrganizationSettings, AuditLog, Person, Employment, ConsentRecord,
BiometricTemplate, Shift, WorkSchedule, Holiday, LeaveRequest, AttendanceEvent,
AttendanceRecord, CorrectionRecord, MissingCheckoutAlert, Device,
DeviceSyncCursor.

Ledger rules:

- `AttendanceEvent`, `ConsentRecord`, `AuditLog`, `CorrectionRecord` are
  append-only. Verified events are never mutated.
- Daily `AttendanceRecord` rows are derived and rebuildable from the ledger.
- Corrections append a `CorrectionRecord` and create a compensating source
  event, then recompute the affected day.
- Idempotency key (unique per org) + time-window dedupe prevent duplicates.
- Offline events carry client-generated idempotency keys.

## 5. Phases

### Phase 1 — Backend core completion (current)

- [x] Inspect repository and write this plan.
- [ ] Migrations + RLS for `attendance` and `devices` (unblocks tests).
- [ ] Config fixes: `token_blacklist`, Celery app + tenant-aware task base,
      `CSRF_TRUSTED_ORIGINS`, Makefile `run-ai` path.
- [ ] `apply_correction()` in the engine.
- [ ] Attendance API: event ingest, event history, daily records, corrections,
      missing-checkout alerts; role-scoped; all queries tenant-filtered.
- [ ] Devices API: pair/rotate token, list, deactivate, sync cursor/offline
      batch ingest.
- [ ] WebSocket consumer + ASGI `ProtocolTypeRouter` for the live feed.
- [ ] Tests for engine, APIs, RLS on new tables, WS auth/tenancy.
- [ ] Full `make test`, `make lint`, typecheck; regenerate OpenAPI + TS types.

Exit criteria: `cd backend && pytest` green; `make codegen` produces a spec that
contains attendance and device contracts; all new tenant tables have RLS.

### Phase 2 — Web application

- App shell: dark navy/charcoal theme, responsive sidebar, auth guard.
- API client generated types only; TanStack Query for all server state.
- Screens: login/MFA, onboarding, dashboard (real aggregates), live feed,
  people, consent/biometrics, schedules, attendance history + corrections,
  devices, branch/department, organization settings, audit log.
- shadcn/ui primitives (Radix-based) and accessible components; no fake stats,
  no placeholder buttons.

Exit criteria: `npm run build` + `npm test` green; every visible number
originates from the API.

### Phase 3 — AI service (independent)

- FastAPI app with internal service token auth; modular pipeline stages:
  authorized capture → detect → quality → liveness → embedding → verification
  → (backend decides) eligibility.
- Pluggable model adapters (YuNet detect, InsightFace ArcFace embedding) with
  explicit model versions and thresholds from config.
- No raw image retention by default; protected templates returned to backend
  for encryption; no covert identification.
- Evaluation harness + report under `docs/ai/evaluation/`. **No accuracy claim
  without a committed report.**

Exit criteria: service tests green; report documents dataset, methodology,
FAR/FRR and limitations.

### Phase 4 — Channel clients

- Mobile (Expo): auth, MFA, self attendance with manual fallback, my history,
  leave requests, offline queue with idempotency keys.
- Terminal (browser kiosk): device pairing, camera capture, QR/PIN fallback,
  online/offline states.
- Both consume generated API types only.

### Phase 5 — Billing, monitoring, deployment

- Subscription plans, entitlements, seat limits enforced server-side in the
  attendance/API layer; Stripe webhooks with signature verification.
- Notifications (in-app + email) and scheduled tasks (missing checkout alerts,
  retention cleanup).
- Prometheus metrics endpoint + scrape config, Sentry (already wired),
  Dockerfiles, nginx TLS config, backup/restore docs.
- Seed command (development only, realistic data).
- CI pipeline running lint/typecheck/tests and schema drift check.

## 6. Quality gates (run after every phase)

```
cd backend && .venv/bin/python -m pytest -q
cd backend && .venv/bin/python -m ruff check .
cd backend && .venv/bin/python -m mypy apps config
make codegen
cd web && npm run typecheck && npm test -- --run
```

## 7. Non-negotiables

- Tenant isolation in every query, task and socket.
- Append-only attendance ledger; corrections, never silent overwrites.
- Face detection/recognition ≠ authorization.
- No accuracy claims without `docs/ai/evaluation/` report.
- Frontend uses generated API types only.
- No fake dashboards, hardcoded stats, or placeholder "done" buttons.
- Real seed data only in development.
