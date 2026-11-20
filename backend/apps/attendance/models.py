from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class AttendanceEvent(BaseModel):
    """Append-only ledger of every attendance signal.

    Verified events are never mutated. Corrections are separate records that
    reference the original event; the materialized daily record is recomputed
    from the ledger.
    """

    class EventType(models.TextChoices):
        CHECK_IN = "check_in"
        CHECK_OUT = "check_out"
        BREAK_START = "break_start"
        BREAK_END = "break_end"

    class Verification(models.TextChoices):
        VERIFIED_FACE = "verified_face"
        VERIFIED_MANUAL = "verified_manual"
        VERIFIED_DEVICE = "verified_device"
        PENDING = "pending"
        REJECTED = "rejected"

    class Source(models.TextChoices):
        WEB = "web"
        MOBILE = "mobile"
        TERMINAL = "terminal"
        MANUAL = "manual"
        IMPORT = "import"
        SYNC = "sync"

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="events")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="events")
    branch = models.ForeignKey("tenants.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    device = models.ForeignKey("devices.Device", null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    occurred_at = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=20, choices=Verification.choices, default=Verification.PENDING)
    verification_score = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=16, choices=Source.choices)
    idempotency_key = models.CharField(max_length=120)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"], name="uniq_event_idempotency_per_org"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "person", "-occurred_at"]),
            models.Index(fields=["organization", "event_type", "-occurred_at"]),
            models.Index(fields=["organization", "verification_status"]),
        ]


class AttendanceRecord(BaseModel):
    """Materialized per-person-per-day state derived from the event ledger."""

    class DayStatus(models.TextChoices):
        PRESENT = "present"
        LATE = "late"
        EARLY_DEPARTURE = "early_departure"
        ABSENT = "absent"
        ON_LEAVE = "on_leave"
        HOLIDAY = "holiday"
        WEEKEND = "weekend"

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="attendance_records")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="attendance_records")
    branch = models.ForeignKey("tenants.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="attendance_records")
    date = models.DateField(db_index=True)
    shift = models.ForeignKey("schedules.Shift", null=True, blank=True, on_delete=models.SET_NULL, related_name="attendance_records")
    first_check_in = models.DateTimeField(null=True, blank=True)
    last_check_out = models.DateTimeField(null=True, blank=True)
    total_work_seconds = models.PositiveIntegerField(default=0)
    total_break_seconds = models.PositiveIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)
    early_minutes = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=DayStatus.choices, default=DayStatus.ABSENT)
    flags = models.JSONField(default=dict, blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "person", "date"], name="uniq_daily_record"),
        ]
        indexes = [models.Index(fields=["organization", "date", "status"])]


class CorrectionRecord(BaseModel):
    """Approved manual correction. Original events remain immutable."""

    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="corrections")
    original_event = models.ForeignKey(AttendanceEvent, on_delete=models.CASCADE, related_name="corrections")
    corrected_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="corrections")
    reason = models.TextField()
    new_occurred_at = models.DateTimeField()
    new_event_type = models.CharField(max_length=16, choices=AttendanceEvent.EventType.choices)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "-applied_at"])]


class MissingCheckoutAlert(BaseModel):
    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="missing_checkouts")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="missing_checkouts")
    date = models.DateField()
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "person", "date"], name="uniq_missing_checkout"),
        ]
