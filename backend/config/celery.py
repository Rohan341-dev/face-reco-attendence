"""Celery application.

Workers receive the resolved tenant identifiers as task keyword arguments and
pin the matching PostgreSQL GUCs through ``TenantTask`` before any database
access, so RLS applies to background work exactly as it does to HTTP requests.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("facetrack")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

TENANT_KWARGS = ("organization_id", "user_id", "device_id", "platform_admin")


class TenantTask(app.Task):
    """Base task that scopes every DB query to the caller's tenant."""

    abstract = True

    def __call__(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        from apps.core.middleware import tenant_context

        org_id = kwargs.get("organization_id")
        user_id = kwargs.get("user_id")
        device_id = kwargs.get("device_id")
        platform_admin = bool(kwargs.get("platform_admin", False))
        with tenant_context(
            org_id,
            user_id=user_id,
            device_id=device_id,
            platform_admin=platform_admin,
        ):
            return self.run(*args, **kwargs)
