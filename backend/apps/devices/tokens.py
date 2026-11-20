"""Short-lived, signed tokens for paired kiosk/camera devices.

A device token is not a user credential: it carries a device id and tenant id,
is verified against the device registry on every request, and is scoped by RLS
through the ``app.current_device`` GUC.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone

TOKEN_TYPE = "device"


def issue_device_token(device) -> str:  # noqa: ANN001
    now = timezone.now()
    minutes = int(getattr(settings, "DEVICE_TOKEN_MINUTES", 60))
    payload = {
        "type": TOKEN_TYPE,
        "device_id": str(device.id),
        "org_id": str(device.organization_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_device_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
    if payload.get("type") != TOKEN_TYPE:
        return None
    if not payload.get("device_id") or not payload.get("org_id"):
        return None
    return payload
