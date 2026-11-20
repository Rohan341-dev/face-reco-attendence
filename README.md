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

## Quality gates

```bash
make check            # lint + typecheck + tests
make codegen          # OpenAPI -> TS types for web/mobile/terminal
```

## Documentation

- `docs/architecture/` — system design, tenancy, RLS
- `docs/security/` — threat model, biometric handling
- `docs/modules/` — per-module docs (attendance engine, AI pipeline, billing)
