# AGENTS.md

## Project

FaceTrack AI — multi-tenant attendance SaaS. Monorepo: `backend` (Django 5/DRF), `ai` (FastAPI), `web` (React 19), `mobile` (Expo), `terminal` (kiosk).

## Commands

- `make install` — venv (Python 3.12) + deps
- `make migrate` — backend migrations
- `make test` — pytest (backend, ai) + vitest (web)
- `make lint` / `make typecheck` / `make check`
- `make codegen` — regenerate OpenAPI → TS types (never hand-edit generated types)

## Rules

- Tenant isolation: every model scoped by `organization_id`; RLS policies required for new tenant tables. Never query tenant data without org context.
- Attendance events are append-only; use correction records, never update verified events.
- Face detection ≠ authorization. Attendance requires full verification pipeline + consent + eligibility checks.
- No fake dashboards, no hardcoded stats, no placeholder buttons marked as done.
- No accuracy claims without an evaluation report in `docs/ai/evaluation/`.
- Frontend consumes generated API types only.
