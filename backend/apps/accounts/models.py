from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseModel


class User(AbstractUser):
    """Global identity. Tenancy membership lives in tenants.Membership."""

    class Meta:
        indexes = [models.Index(fields=["email"])]

    email = models.EmailField(unique=True)
    is_platform_admin = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret_encrypted = models.TextField(blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = ["username"]

    def __str__(self) -> str:
        return self.email


class MFADevice(BaseModel):
    """MFA lifecycle audit trail (enable/disable/challenge outcomes)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mfa_events")
    event = models.CharField(max_length=32)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
