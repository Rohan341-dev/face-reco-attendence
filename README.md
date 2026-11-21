# FaceTrack AI

Multi-tenant AI-powered attendance & workforce automation SaaS.

## Stack

- **backend/** — Django 5 + DRF + PostgreSQL (RLS) + Redis + Celery + Django Channels + JWT
- **ai/** — FastAPI face pipeline (YuNet detection, InsightFace ArcFace embeddings, liveness, evaluation harness)
- **web/** — React 19 + TypeScript + Tailwind + shadcn/ui + TanStack Query (org dashboard + platform admin)
- **mobile/** — React Native + Expo
- **terminal/** — camera attendance terminal (browser kiosk)

## Quick start (local, no Docker required)

```bash
make install          # py3.12 venv + deps + web node_modules
make db-up            # Postgres + Redis (homebrew or docker)
cp .env.example .env  # fill BIOMETRIC_KEY_BASE64
make migrate
make run-backend      # http://localhost:8000
make run-ai           # http://localhost:8001
make run-web          # http://localhost:5173
```

## Implemented

- Multi-tenant backend: JWT + TOTP MFA, RBAC, PostgreSQL RLS on every tenant
  table, people/consent/biometrics, schedules/leave/holidays.
- Central attendance engine with eligibility checks, idempotency, dedupe,
  overnight shifts, immutable ledger, append-only corrections, offline sync.
- Attendance and device HTTP APIs, signed short-lived device tokens, WebSocket
  live feed, tenant-aware Celery tasks, Prometheus metrics.
- Web dashboard (real API integration), browser terminal kiosk with camera
  preview and offline queue, Expo mobile source.
- FastAPI AI service with modular pipeline; **default embedding backend is a
  deterministic stub** and liveness is a heuristic, not certified PAD.

## Quality gates

```bash
make check            # lint + typecheck + tests
make codegen          # OpenAPI -> TS types for web/mobile/terminal
```

`make check` currently runs backend + AI + web tests. Terminal and mobile are
verified with `npm run typecheck` (and `npm run build` for terminal) from their
directories. Mobile dependencies must be installed with `npm install` in
`mobile/` before typechecking.

## Not yet implemented

- Subscription/billing enforcement (the `billing` app is an empty placeholder).
- Evaluation of the recognition model on real data; no accuracy is claimed.
- Backup/restore runbook and CI/CD pipeline.

## Documentation

- `docs/architecture/IMPLEMENTATION_PLAN.md` — phased plan and status
- `docs/architecture/deployment.md` — Docker/Nginx/Prometheus setup
- `docs/security/threat-model.md` — controls and residual risks
- `docs/modules/attendance-engine.md`, `docs/modules/ai-pipeline.md`
- `docs/ai/evaluation/INITIAL_REPORT.md` — evaluation status (no claims)

