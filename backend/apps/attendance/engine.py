"""Central attendance engine.

Every channel (web, mobile, terminal, manual correction, offline sync) funnels
into :func:`process_event`. The engine is the single place that enforces
consent, device authorization, duplicate prevention and schedule evaluation.
AttendanceEvent rows are append-only; daily records are derived materialized
views rebuilt from the event ledger.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Q

from apps.attendance.models import AttendanceEvent, AttendanceRecord, MissingCheckoutAlert
from apps.people.models import Person, has_active_consent
from apps.schedules.models import Holiday, LeaveRequest, WorkSchedule
from apps.tenants.models import Organization, OrganizationSettings

logger = logging.getLogger(__name__)


class AttendanceError(Exception):
    code = "attendance_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DuplicateEvent(AttendanceError):
    code = "duplicate_event"


class IneligibleEvent(AttendanceError):
    code = "ineligible_event"


@dataclass
class EventInput:
    person_id: str
    event_type: str
    occurred_at: datetime
    source: str
    idempotency_key: str
    verification_status: str = AttendanceEvent.Verification.PENDING
    verification_score: float | None = None
    device_id: str | None = None
    branch_id: str | None = None
    metadata: dict | None = None


def _org_timezone(org: Organization) -> ZoneInfo:
    try:
        return ZoneInfo(org.timezone)
    except Exception:  # noqa: BLE001
        return ZoneInfo("UTC")


def _local_date(occurred_at: datetime, org: Organization) -> date:
    return occurred_at.astimezone(_org_timezone(org)).date()


def validate_eligibility(org_id: str, data: EventInput) -> Person:
    person = Person.objects.filter(pk=data.person_id, organization_id=org_id).first()
    if person is None or person.status != Person.Status.ACTIVE:
        raise IneligibleEvent("Person is not active in this organization.")
    settings = OrganizationSettings.objects.filter(organization_id=org_id).first()
    require_liveness = settings.require_liveness if settings else True
    allow_manual = settings.allow_manual_attendance if settings else True

    if data.verification_status == AttendanceEvent.Verification.VERIFIED_FACE:
        if not has_active_consent(org_id, person.id, "biometric_attendance"):
            raise IneligibleEvent("No active biometric consent for this person.")
        if require_liveness and not (data.metadata or {}).get("liveness_passed"):
            raise IneligibleEvent("Liveness check did not pass.")
        if data.verification_score is None:
            raise IneligibleEvent("Face verification score is required.")
    elif data.verification_status == AttendanceEvent.Verification.VERIFIED_MANUAL:
        if not allow_manual:
            raise IneligibleEvent("Manual attendance is disabled for this organization.")
    elif data.verification_status == AttendanceEvent.Verification.VERIFIED_DEVICE:
        if not data.device_id:
            raise IneligibleEvent("Device authorization is required for device-verified events.")
    elif data.verification_status in (
        AttendanceEvent.Verification.PENDING,
        AttendanceEvent.Verification.REJECTED,
    ):
        raise IneligibleEvent("Event is not verified; attendance cannot be recorded.")

    if data.device_id:
        from apps.devices.models import Device

        device = Device.objects.filter(pk=data.device_id, organization_id=org_id, is_active=True).first()
        if not device:
            raise IneligibleEvent("Source device is not authorized for this organization.")
        if data.branch_id and device.branch_id and str(device.branch_id) != str(data.branch_id):
            raise IneligibleEvent("Device is not authorized for this branch.")
        if data.branch_id is None:
            data.branch_id = str(device.branch_id) if device.branch_id else None
    return person


@transaction.atomic
def process_event(org_id: str, data: EventInput) -> tuple[AttendanceEvent, bool]:
    """Create an event (idempotently) and recompute the affected daily record.

    Returns ``(event, created)``; duplicates return the original event with
    ``created=False`` instead of inserting a second row.
    """
    existing = AttendanceEvent.objects.filter(
        organization_id=org_id, idempotency_key=data.idempotency_key
    ).first()
    if existing:
        return existing, False

    person = validate_eligibility(org_id, data)
    settings = OrganizationSettings.objects.filter(organization_id=org_id).first()
    window = settings.dedupe_window_seconds if settings else 120
    previous = (
        AttendanceEvent.objects.filter(
            organization_id=org_id,
            person_id=person.id,
            event_type=data.event_type,
            occurred_at__range=(
                data.occurred_at - timedelta(seconds=window),
                data.occurred_at + timedelta(seconds=window),
            ),
        )
        .order_by("-occurred_at")
        .first()
    )
    if previous:
        logger.info("Duplicate event suppressed person=%s type=%s", person.id, data.event_type)
        raise DuplicateEvent("An equivalent event already exists within the dedupe window.")

    event = AttendanceEvent.objects.create(
        organization_id=org_id,
        person_id=person.id,
        branch_id=data.branch_id or None,
        device_id=data.device_id or None,
        event_type=data.event_type,
        occurred_at=data.occurred_at,
        verification_status=data.verification_status,
        verification_score=data.verification_score,
        source=data.source,
        idempotency_key=data.idempotency_key,
        metadata=data.metadata or {},
    )

    org = Organization.objects.get(pk=org_id)
    local_date = _local_date(event.occurred_at, org)
    recompute_daily_record(org_id, person.id, local_date)
    broadcast(org_id, event, local_date)
    return event, True


def broadcast(org_id: str, event: AttendanceEvent, local_date: date) -> None:
    try:
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"attendance_{org_id}",
            {
                "type": "attendance.event",
                "event": {
                    "id": str(event.id),
                    "person_id": str(event.person_id),
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at.isoformat(),
                    "verification_status": event.verification_status,
                    "source": event.source,
                    "date": local_date.isoformat(),
                },
            },
        )
    except Exception as exc:  # noqa: BLE001 — realtime is best-effort
        logger.warning("Live feed broadcast failed: %s", exc)


def _active_shift(org_id: str, person, on_date: date) -> tuple[WorkSchedule | None, object | None]:
    schedules = WorkSchedule.objects.filter(
        organization_id=org_id,
        person_id=person.id,
        effective_from__lte=on_date,
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=on_date))
    for assignment in schedules.select_related("shift"):
        days = assignment.days_of_week or []
        if not days or on_date.weekday() in [int(d) for d in days]:
            return assignment, assignment.shift
    return None, None


def _window_bounds(shift, on_date: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(on_date, shift.start_time, tzinfo=tz)
    if shift.end_time > shift.start_time:
        end = datetime.combine(on_date, shift.end_time, tzinfo=tz)
    else:
        end = datetime.combine(on_date + timedelta(days=1), shift.end_time, tzinfo=tz)
    return start, end


@transaction.atomic
def recompute_daily_record(org_id: str, person_id: str, on_date: date) -> AttendanceRecord:
    """Rebuild a person's daily record from immutable events."""
    org = Organization.objects.get(pk=org_id)
    tz = _org_timezone(org)
    person = Person.objects.get(pk=person_id, organization_id=org_id)
    assignment, shift = _active_shift(org_id, person, on_date)

    events = list(
        AttendanceEvent.objects.filter(
            organization_id=org_id,
            person_id=person_id,
            occurred_at__date=on_date,
        ).order_by("occurred_at")
    )
    # Overnight shifts: a check-in shortly after midnight belongs to the
    # previous day's shift window (example: 22:00-06:00).
    if shift and shift.is_overnight:
        midnight_utc = datetime.combine(on_date, time(0, 0), tzinfo=tz).astimezone(dt_timezone.utc)
        cross = AttendanceEvent.objects.filter(
            organization_id=org_id,
            person_id=person_id,
            event_type=AttendanceEvent.EventType.CHECK_IN,
            occurred_at__gte=midnight_utc - timedelta(hours=12),
            occurred_at__lt=midnight_utc,
        )
        events = sorted([*cross, *events], key=lambda e: e.occurred_at)

    check_ins = [e.occurred_at for e in events if e.event_type == AttendanceEvent.EventType.CHECK_IN]
    check_outs = [e.occurred_at for e in events if e.event_type == AttendanceEvent.EventType.CHECK_OUT]
    breaks: list[tuple[datetime, datetime]] = []
    pending_break = None
    for event in events:
        if event.event_type == AttendanceEvent.EventType.BREAK_START:
            pending_break = event.occurred_at
        elif event.event_type == AttendanceEvent.EventType.BREAK_END and pending_break:
            breaks.append((pending_break, event.occurred_at))
            pending_break = None

    first_check_in = min(check_ins) if check_ins else None
    last_check_out = max(check_outs) if check_outs else None
    break_seconds = int(sum((end - start).total_seconds() for start, end in breaks))
    work_seconds = 0
    if first_check_in and last_check_out and last_check_out > first_check_in:
        work_seconds = max(0, int((last_check_out - first_check_in).total_seconds()) - break_seconds)

    late_minutes = 0
    early_minutes = 0
    if shift:
        start, end = _window_bounds(shift, on_date, tz)
        grace = shift.grace_minutes
        if first_check_in and first_check_in > start:
            late_minutes = max(0, int((first_check_in - start).total_seconds() // 60) - grace)
        if last_check_out and last_check_out < end:
            early_minutes = max(0, int((end - last_check_out).total_seconds() // 60) - grace)

    on_leave = LeaveRequest.objects.filter(
        organization_id=org_id,
        person_id=person_id,
        status=LeaveRequest.Status.APPROVED,
        start_date__lte=on_date,
        end_date__gte=on_date,
    ).exists()
    holiday = Holiday.objects.filter(organization_id=org_id, date=on_date).first()

    flags: dict = {}
    if on_leave:
        status = AttendanceRecord.DayStatus.ON_LEAVE
        flags["on_leave"] = True
    elif holiday and not holiday.is_working_day and not events:
        status = AttendanceRecord.DayStatus.HOLIDAY
        flags["holiday"] = holiday.name
    elif not events:
        status = AttendanceRecord.DayStatus.ABSENT
    elif late_minutes and not early_minutes:
        status = AttendanceRecord.DayStatus.LATE
        flags["late"] = True
    elif early_minutes and not late_minutes:
        status = AttendanceRecord.DayStatus.EARLY_DEPARTURE
        flags["early_departure"] = True
    elif late_minutes and early_minutes:
        status = AttendanceRecord.DayStatus.LATE
        flags.update({"late": True, "early_departure": True})
    else:
        status = AttendanceRecord.DayStatus.PRESENT

    if first_check_in and not last_check_out and not on_leave:
        MissingCheckoutAlert.objects.get_or_create(
            organization_id=org_id, person_id=person_id, date=on_date
        )
        flags["missing_checkout"] = True

    record, _ = AttendanceRecord.objects.update_or_create(
        organization_id=org_id,
        person_id=person_id,
        date=on_date,
        defaults={
            "branch_id": events[0].branch_id if events else None,
            "shift": shift,
            "first_check_in": first_check_in,
            "last_check_out": last_check_out,
            "total_work_seconds": work_seconds,
            "total_break_seconds": break_seconds,
            "late_minutes": late_minutes,
            "early_minutes": early_minutes,
            "status": status,
            "flags": flags,
        },
    )
    return record
