"""Attendance engine + API tests: eligibility, ledger, corrections, isolation."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.attendance.engine import EventInput, IneligibleEvent, process_event
from apps.attendance.models import AttendanceEvent, AttendanceRecord, CorrectionRecord, MissingCheckoutAlert
from apps.core.models import AuditLog
from tests.conftest import tenant_ctx


def _person(client, name: str) -> str:
    response = client.post(
        "/api/people/",
        {"employee_id": f"E-{name}", "first_name": name, "email": f"{name}@acme.test"},
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data["id"]


def _event(client, person_id: str, event_type: str, when, **extra) -> dict:
    payload = {
        "person_id": person_id,
        "event_type": event_type,
        "occurred_at": when.isoformat(),
        "source": "web",
        "idempotency_key": f"{event_type}-{when.timestamp()}",
        **extra,
    }
    payload.update(extra)
    return client.post("/api/attendance/events/", payload, format="json")


@pytest.mark.django_db(transaction=True)
def test_pending_and_unconsented_events_are_rejected(auth):
    client, _ = auth()
    person_id = _person(client, "Reject")
    now = timezone.now()

    pending = _event(client, person_id, "check_in", now, verification_status="pending")
    assert pending.status_code == 422
    assert pending.data["error"]["code"] == "ineligible_event"

    face = _event(client, person_id, "check_in", now, verification_status="verified_face", verification_score=0.9)
    assert face.status_code == 422
    assert "consent" in face.data["error"]["detail"].lower()

    granted = client.post(
        f"/api/people/{person_id}/consents/grant/",
        {"purpose": "biometric_attendance", "evidence": "signed"},
        format="json",
    )
    assert granted.status_code == 201

    no_liveness = _event(
        client, person_id, "check_in", now,
        verification_status="verified_face", verification_score=0.9, metadata={},
    )
    assert no_liveness.status_code == 422
    assert "liveness" in no_liveness.data["error"]["detail"].lower()

    valid = _event(
        client, person_id, "check_in", now,
        verification_status="verified_face", verification_score=0.9,
        metadata={"liveness_passed": True},
    )
    assert valid.status_code == 201, valid.data
    assert valid.data["verification_status"] == "verified_face"


@pytest.mark.django_db(transaction=True)
def test_idempotency_and_dedupe_window(auth):
    client, _ = auth()
    person_id = _person(client, "Dedupe")
    now = timezone.now()
    payload = {
        "person_id": person_id,
        "event_type": "check_in",
        "occurred_at": now.isoformat(),
        "source": "manual",
        "idempotency_key": "offline-key-1",
        "verification_status": "verified_manual",
    }
    first = client.post("/api/attendance/events/", payload, format="json")
    assert first.status_code == 201
    same = client.post("/api/attendance/events/", payload, format="json")
    assert same.status_code == 200
    assert same.data["id"] == first.data["id"]

    near_duplicate = client.post(
        "/api/attendance/events/",
        {**payload, "idempotency_key": "offline-key-2", "occurred_at": (now + timedelta(seconds=30)).isoformat()},
        format="json",
    )
    assert near_duplicate.status_code == 409
    assert near_duplicate.data["error"]["code"] == "duplicate_event"


@pytest.mark.django_db(transaction=True)
def test_daily_record_work_time_break_and_missing_checkout(auth, onboard):
    client, tokens = auth()
    person_id = _person(client, "Workday")
    day = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
    check_in = _event(client, person_id, "check_in", day, verification_status="verified_manual")
    assert check_in.status_code == 201
    break_start = _event(client, person_id, "break_start", day + timedelta(hours=2), verification_status="verified_manual")
    break_end = _event(client, person_id, "break_end", day + timedelta(hours=2, minutes=30), verification_status="verified_manual")
    assert break_start.status_code == 201 and break_end.status_code == 201

    records = client.get("/api/attendance/records/").data
    record = next(r for r in records if str(r["person"]) == person_id)
    assert record["total_break_seconds"] == 1800
    assert record["flags"].get("missing_checkout") is True

    alerts = client.get("/api/attendance/missing-checkouts/?resolved=false").data
    assert any(a["person"] == person_id for a in alerts)

    alert_id = next(a["id"] for a in alerts if a["person"] == person_id)
    resolved = client.post(f"/api/attendance/missing-checkouts/{alert_id}/resolve/", {}, format="json")
    assert resolved.status_code == 200 and resolved.data["resolved_at"] is not None

    checkout = _event(client, person_id, "check_out", day + timedelta(hours=8), verification_status="verified_manual")
    assert checkout.status_code == 201
    record = next(r for r in client.get("/api/attendance/records/").data if str(r["person"]) == person_id)
    assert record["total_work_seconds"] == 7 * 3600
    assert record["status"] == "present"


@pytest.mark.django_db(transaction=True)
def test_correction_is_append_only_and_rebuilds_record(auth):
    client, tokens = auth()
    person_id = _person(client, "Fix")
    day = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    event = _event(client, person_id, "check_in", day, verification_status="verified_manual")
    original_id = event.data["id"]

    corrected_at = day + timedelta(minutes=25)
    correction = client.post(
        "/api/attendance/corrections/",
        {
            "original_event": original_id,
            "new_occurred_at": corrected_at.isoformat(),
            "new_event_type": "check_in",
            "reason": "Kiosk clock was 25 minutes fast",
        },
        format="json",
    )
    assert correction.status_code == 201, correction.data

    with tenant_ctx(tokens["org_id"]):
        original = AttendanceEvent.objects.get(pk=original_id)
        assert original.occurred_at == day
        assert CorrectionRecord.objects.filter(original_event_id=original_id).count() == 1
        assert AuditLog.objects.filter(action="attendance_corrected").exists()

    record = next(r for r in client.get("/api/attendance/records/").data if str(r["person"]) == person_id)
    assert record["first_check_in"] == corrected_at.isoformat().replace("+00:00", "Z")


@pytest.mark.django_db(transaction=True)
def test_non_hr_cannot_correct_attendance(auth):
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    from apps.tenants.models import Membership

    client, tokens = auth()
    person_id = _person(client, "Employee")
    event = _event(client, person_id, "check_in", timezone.now(), verification_status="verified_manual")

    with tenant_ctx(tokens["org_id"]):
        user = get_user_model().objects.create_user(
            username="worker-role", email="worker-role@acme.test", password="Str0ngPass!42"
        )
        Membership.objects.create(
            user=user, organization_id=tokens["org_id"], role=Membership.Role.EMPLOYEE
        )

    worker = APIClient()
    login = worker.post(
        "/api/auth/login/",
        {"email": "worker-role@acme.test", "password": "Str0ngPass!42"},
        format="json",
    )
    assert login.status_code == 200, login.data
    worker.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    denied = worker.post(
        "/api/attendance/corrections/",
        {
            "original_event": event.data["id"],
            "new_occurred_at": timezone.now().isoformat(),
            "new_event_type": "check_in",
            "reason": "test",
        },
        format="json",
    )
    assert denied.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_offline_sync_reports_partial_results_and_cross_tenant_isolation(auth, onboard):
    client, tokens = auth()
    person_id = _person(client, "Sync")
    now = timezone.now()
    batch = {
        "events": [
            {
                "person_id": person_id,
                "event_type": "check_in",
                "occurred_at": now.isoformat(),
                "source": "sync",
                "idempotency_key": "sync-1",
                "verification_status": "verified_manual",
            },
            {
                "person_id": "00000000-0000-0000-0000-000000000000",
                "event_type": "check_in",
                "occurred_at": now.isoformat(),
                "source": "sync",
                "idempotency_key": "sync-2",
                "verification_status": "verified_manual",
            },
        ]
    }
    response = client.post("/api/attendance/sync/", batch, format="json")
    assert response.status_code == 207
    assert [item["status"] for item in response.data["results"]] == ["accepted", "rejected"]

    _, _, other = onboard("Globex", "globex", "owner@globex.test")
    assert all(e["person"] != person_id for e in other.get("/api/attendance/events/").data)

    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant', %s, true)", ["00000000-0000-0000-0000-000000000000"])
        cursor.execute("SELECT count(*) FROM attendance_attendanceevent")
        assert cursor.fetchone()[0] == 0


@pytest.mark.django_db(transaction=True)
def test_engine_direct_call_requires_verification(auth):
    client, tokens = auth()
    person_id = _person(client, "Engine")
    with tenant_ctx(tokens["org_id"]):
        data = EventInput(
            person_id=person_id,
            event_type="check_in",
            occurred_at=timezone.now(),
            source="web",
            idempotency_key="direct-1",
        )
        with pytest.raises(IneligibleEvent):
            process_event(tokens["org_id"], data)
        assert AttendanceEvent.objects.count() == 0
