from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class Shift(BaseModel):
    """A recurring work window. End time <= start time means overnight."""

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="shifts")
    name = models.CharField(max_length=120)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveSmallIntegerField(default=0)
    grace_minutes = models.PositiveSmallIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_shift_name_per_org"),
        ]
        indexes = [models.Index(fields=["organization", "is_active"])]

    @property
    def is_overnight(self) -> bool:
        return self.end_time <= self.start_time

    def clean(self) -> None:
        if self.is_overnight and self.start_time == self.end_time:
            raise ValidationError("Shift start and end times must differ.")
        if self.break_minutes > 480:
            raise ValidationError("Break duration is too long.")


class WorkSchedule(BaseModel):
    """Assigns a person to a shift for a date range on selected weekdays."""

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="work_schedules")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="schedules")
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="assignments")
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    days_of_week = models.JSONField(default=list)  # [0..6] Mon..Sun; [] = all days

    class Meta:
        indexes = [
            models.Index(fields=["organization", "person", "effective_from"]),
        ]

    def clean(self) -> None:
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError("effective_to cannot precede effective_from.")
        if any(not (0 <= int(day) <= 6) for day in self.days_of_week):
            raise ValidationError("days_of_week values must be 0..6.")


class Holiday(BaseModel):
    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="holidays")
    name = models.CharField(max_length=150)
    date = models.DateField()
    is_working_day = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "date"], name="uniq_holiday_date_per_org"),
        ]
        indexes = [models.Index(fields=["organization", "date"])]


class LeaveRequest(BaseModel):
    class Type(models.TextChoices):
        CASUAL = "casual"
        SICK = "sick"
        PAID = "paid"
        UNPAID = "unpaid"
        OTHER = "other"

    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"
        CANCELLED = "cancelled"

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="leave_requests")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=16, choices=Type.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    decided_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="leave_decisions"
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "status", "start_date"])]

    def clean(self) -> None:
        if self.end_date < self.start_date:
            raise ValidationError("end_date cannot precede start_date.")
