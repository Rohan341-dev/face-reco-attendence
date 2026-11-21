# Deployment

## Services

`docker-compose.yml` defines Postgres, Redis, Django (gunicorn WSGI), the
FastAPI AI service, a Celery worker, Daphne (ASGI/WebSocket) and Nginx.

- Django: `backend/Dockerfile`
- AI: `ai/Dockerfile`
- Nginx: `deploy/nginx/nginx.conf`, `deploy/nginx/conf.d/facetrack.conf`
- Certificates: mount `fullchain.pem` and `privkey.pem` into
  `deploy/nginx/certs/` (gitignored by convention; the directory contains a
  placeholder file only).
- Prometheus: `deploy/prometheus/prometheus.yml`; the scrape token file must
  contain the Django `SECRET_KEY`.

## Required environment

See `.env.example`. In production set a strong `SECRET_KEY`, a real
`BIOMETRIC_KEY_BASE64`, `SENTRY_DSN`, HTTPS origins in `CORS_ALLOWED_ORIGINS`
and `CSRF_TRUSTED_ORIGINS`, and `DJANGO_SETTINGS_MODULE=config.settings.prod`.

## Migrations and startup

```
docker compose up -d postgres redis
docker compose run --rm backend python manage.py migrate
docker compose up -d
```

## Observability

- Prometheus histogram/counter at `/api/metrics/` (bearer token required).
- Sentry enabled in `config/settings/prod.py` when `SENTRY_DSN` is set.
- Structured console logs from Django, Celery and Daphne.

## Data protection

Nightly `pg_dump` backups and periodic restore drills are required before
production use; see the runbook to be added under `docs/security/`.
