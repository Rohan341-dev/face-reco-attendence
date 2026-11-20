"""DRF authentication for paired devices using ``Authorization: Device <jwt>``."""

from __future__ import annotations

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Device
from .tokens import decode_device_token


class DevicePrincipal:
    """Minimal authenticated principal representing a registered device."""

    is_authenticated = True
    is_anonymous = False
    is_device = True

    def __init__(self, device: Device):
        self.device = device
        self.id = device.id
        self.pk = device.id
        self.organization_id = device.organization_id
        self.is_active = device.is_active

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"device:{self.id}"


class DeviceAuthentication(BaseAuthentication):
    keyword = "Device"

    def authenticate(self, request):  # noqa: ANN001, ANN201
        header = request.META.get("HTTP_AUTHORIZATION", "")
        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None
        payload = decode_device_token(parts[1])
        if payload is None:
            raise AuthenticationFailed("Invalid or expired device token.")
        device = Device.objects.filter(
            pk=payload["device_id"],
            organization_id=payload["org_id"],
            is_active=True,
        ).first()
        if device is None:
            raise AuthenticationFailed("Device is not registered or has been deactivated.")
        device.last_seen_at = timezone.now()
        device.save(update_fields=["last_seen_at", "updated_at"])
        return DevicePrincipal(device), parts[1]

    def authenticate_header(self, request):  # noqa: ANN001, ANN201
        return self.keyword
