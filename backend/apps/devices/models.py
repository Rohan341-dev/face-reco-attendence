from __future__ import annotations

import hashlib
import secrets

from django.db import models

from apps.core.models import BaseModel


class Device(BaseModel):
    class Kind(models.TextChoices):
        TERMINAL = "terminal"
        CAMERA = "camera"
        MOBILE = "mobile"

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="devices")
    branch = models.ForeignKey("tenants.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="devices")
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.TERMINAL)
    token_hash = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    paired_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "is_active"])]

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def issue_token(cls) -> str:
        return secrets.token_urlsafe(32)


class DeviceSyncCursor(BaseModel):
    """Offline sync watermark for a device.

    ``organization`` is denormalized from the device so the table can be
    covered by the same org-scoped RLS policy as every other tenant table.
    """

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="device_sync_cursors")
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name="sync_cursor")
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_event_id = models.CharField(max_length=40, blank=True, default="")
