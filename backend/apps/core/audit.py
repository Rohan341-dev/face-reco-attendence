"""Audit logging helper. Audit rows are append-only by convention and by
RLS policy (no UPDATE/DELETE policies are created for them)."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from apps.core.models import AuditLog

logger = logging.getLogger(__name__)


def client_ip(request) -> str | None:  # noqa: ANN001
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(
    action: str,
    *,
    organization_id=None,  # noqa: ANN001
    actor=None,  # noqa: ANN001
    object_repr: str = "",
    changes: dict[str, Any] | None = None,
    request=None,  # noqa: ANN001
    actor_label: str = "",
) -> AuditLog | None:
    try:
        with transaction.atomic():
            return AuditLog.objects.create(
                organization_id=organization_id,
                actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
                actor_label=actor_label or (str(actor) if actor else "system"),
                action=action,
                object_repr=object_repr[:300],
                changes=changes or {},
                ip_address=client_ip(request),
            )
    except Exception:  # noqa: BLE001 — audit must never break the main flow, but failures are logged
        logger.exception("Failed to write audit log action=%s", action)
        return None
