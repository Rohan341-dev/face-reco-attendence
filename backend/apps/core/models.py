import uuid

from django.db import models


class BaseModel(models.Model):
    """UUID primary key base model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedModel(BaseModel):
    """Base for every tenant-scoped row. Requires subclasses to define
    an `organization` FK (defined in subclasses to keep import order clean)
    and an RLS policy in the same migration."""

    class Meta:
        abstract = True


class AuditLog(BaseModel):
    """Append-only security/audit trail. Never updated or deleted."""

    class Action(models.TextChoices):
        LOGIN = "login"
        LOGIN_FAILED = "login_failed"
        MFA_ENABLED = "mfa_enabled"
        MFA_DISABLED = "mfa_disabled"
        MFA_CHALLENGE_PASSED = "mfa_challenge_passed"
        MFA_CHALLENGE_FAILED = "mfa_challenge_failed"
        MEMBER_ADDED = "member_added"
        MEMBER_ROLE_CHANGED = "member_role_changed"
        MEMBER_REMOVED = "member_removed"
        CONSENT_GRANTED = "consent_granted"
        CONSENT_WITHDRAWN = "consent_withdrawn"
        BIOMETRIC_ENROLLED = "biometric_enrolled"
        BIOMETRIC_DELETED = "biometric_deleted"
        ATTENDANCE_CORRECTED = "attendance_corrected"
        DEVICE_AUTH = "device_auth"
        DEVICE_REVOKED = "device_revoked"
        DATA_EXPORTED = "data_exported"
        DATA_DELETED = "data_deleted"
        SUBSCRIPTION_CHANGED = "subscription_changed"
        OTHER = "other"

    organization = models.ForeignKey(
        "tenants.Organization", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    actor = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    actor_label = models.CharField(max_length=200, blank=True, default="")
    action = models.CharField(max_length=32, choices=Action.choices)
    object_repr = models.CharField(max_length=300, blank=True, default="")
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "action", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.action} {self.object_repr}"
