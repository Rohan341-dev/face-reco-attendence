from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Person(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active"
        INACTIVE = "inactive"
        SUSPENDED = "suspended"

    organization = models.ForeignKey(
        "tenants.Organization", on_delete=models.CASCADE, related_name="people"
    )
    branch = models.ForeignKey(
        "tenants.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="people"
    )
    department = models.ForeignKey(
        "tenants.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="people"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="person_profile",
    )
    employee_id = models.CharField(max_length=64, blank=True, default="")
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    date_of_joining = models.DateField(null=True, blank=True)
    date_of_leaving = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "employee_id"], name="uniq_employee_id_per_org",
                condition=~models.Q(employee_id=""),
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "branch"]),
            models.Index(fields=["organization", "last_name", "first_name"]),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_name(self) -> str:
        return str(self)


class Employment(BaseModel):
    """Job details, kept separate from the person's identity record."""

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="employments")
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name="employment")
    job_title = models.CharField(max_length=150, blank=True, default="")
    employment_type = models.CharField(max_length=32, default="full_time")
    manager = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports"
    )

    class Meta:
        indexes = [models.Index(fields=["organization", "person"])]


class ConsentRecord(BaseModel):
    """Append-only consent evidence. Withdrawal is a new row, never an update."""

    class Purpose(models.TextChoices):
        BIOMETRIC_ATTENDANCE = "biometric_attendance"
        IMAGE_PROCESSING = "image_processing"
        ANALYTICS = "analytics"

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="consents")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="consents")
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    granted = models.BooleanField(default=True)
    effective_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    evidence = models.CharField(max_length=300, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-effective_at"]
        indexes = [models.Index(fields=["organization", "person", "purpose", "-effective_at"])]


def has_active_consent(organization_id, person_id, purpose: str) -> bool:  # noqa: ANN001
    """True only when the latest append-only consent record grants purpose."""
    record = (
        ConsentRecord.objects.filter(
            organization_id=organization_id, person_id=person_id, purpose=purpose
        )
        .order_by("-effective_at")
        .first()
    )
    return bool(record and record.granted)


class BiometricTemplate(BaseModel):
    """Encrypted face embedding only — no raw images, no plaintext vectors.

    Similarity is computed inside the AI service after an authorized,
    authenticated decrypt, never with a database-side pgvector search over
    plaintext biometric data.
    """

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="biometric_templates")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="biometric_templates")
    encrypted_template = models.TextField()
    model_version = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "person", "is_active"])]
