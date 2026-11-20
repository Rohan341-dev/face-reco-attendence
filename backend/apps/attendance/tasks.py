"""Tenant-scoped background tasks for attendance."""

from __future__ import annotations

from datetime import date, timedelta

from celery.utils.log import get_task_logger
from django.utils import timezone

from config.celery import TenantTask, app

from .engine import recompute_daily_record
from .models import AttendanceRecord, MissingCheckoutAlert

logger = get_task_logger(__name__)


@app.task(base=TenantTask, bind=True, name="attendance.scan_missing_checkouts", max_retries=3)
def scan_missing_checkouts(self, organization_id: str, on_date: str | None = None):  # noqa: ANN001, ANN201
    """Create alerts for checked-in people who never checked out.

    ``TenantTask`` pins ``organization_id`` as the RLS context for the whole
    task before this function runs.
    """
    day = date.fromisoformat(on_date) if on_date else (timezone.localdate() - timedelta(days=1))
    records = AttendanceRecord.objects.filter(
        first_check_in__isnull=False,
        last_check_out__isnull=True,
        date=day,
    ).exclude(status=AttendanceRecord.DayStatus.ON_LEAVE)
    created = 0
    for record in records:
        _, was_created = MissingCheckoutAlert.objects.get_or_create(
            organization_id=record.organization_id,
            person_id=record.person_id,
            date=day,
        )
        created += int(was_created)
    logger.info("Missing checkout scan date=%s created=%s", day, created)
    return {"date": day.isoformat(), "created": created}


@app.task(base=TenantTask, bind=True, name="attendance.recompute_day", max_retries=3)
def recompute_day(self, organization_id: str, person_id: str, on_date: str):  # noqa: ANN001, ANN201
    """Rebuild a person's daily record (used after offline sync / repairs)."""
    record = recompute_daily_record(organization_id, person_id, date.fromisoformat(on_date))
    return {"record_id": str(record.id)}
