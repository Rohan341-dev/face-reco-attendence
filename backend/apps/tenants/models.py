from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Organization(BaseModel):
    """Tenant root. Branches, departments, people, attendance, devices,
    schedules, settings and billing all hang off this row."""

    class Industry(models.TextChoices):
        SCHOOL = "school"
        COLLEGE = "college"
        OFFICE = "office"
        FACTORY = "factory"
        HOSPITAL = "hospital"
        RETAIL = "retail"
        OTHER = "other"

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    industry = models.CharField(max_length=16, choices=Industry.choices, default=Industry.OTHER)
    is_active = models.BooleanField(default=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")

    class Meta:
        verbose_name = "organization"
        indexes = [models.Index(fields=["slug"])]

    def __str__(self) -> str:
        return self.name


class Branch(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=32, blank=True, default="")
    address = models.TextField(blank=True, default="")
    timezone = models.CharField(max_length=64, default="UTC")
    is_headquarters = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_branch_code_per_org"),
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_branch_name_per_org"),
        ]
        indexes = [models.Index(fields=["organization", "is_active"])]

    def __str__(self) -> str:
        return f"{self.organization.name} / {self.name}"


class Department(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="departments")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="departments")
    name = models.CharField(max_length=200)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_dept_name_per_org"),
        ]
        indexes = [models.Index(fields=["organization"])]

    def __str__(self) -> str:
        return self.name


class Membership(BaseModel):
    class Role(models.TextChoices):
        OWNER = "owner"
        ADMIN = "admin"
        HR = "hr"
        MANAGER = "manager"
        EMPLOYEE = "employee"
        AUDITOR = "auditor"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.EMPLOYEE)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "organization"], name="uniq_membership_user_org"),
        ]
        indexes = [models.Index(fields=["organization", "role"])]

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization} ({self.role})"


class OrganizationSettings(BaseModel):
    """Per-tenant behaviour toggles consumed by the attendance engine."""

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="settings")
    grace_minutes_late = models.PositiveSmallIntegerField(default=5)
    grace_minutes_early = models.PositiveSmallIntegerField(default=5)
    require_liveness = models.BooleanField(default=True)
    allow_manual_attendance = models.BooleanField(default=True)
    biometric_retention_days = models.PositiveIntegerField(default=90)
    image_retention_hours = models.PositiveIntegerField(default=0)  # 0 = discard after processing
    dedupe_window_seconds = models.PositiveIntegerField(default=120)

    def __str__(self) -> str:
        return f"Settings {self.organization}"
