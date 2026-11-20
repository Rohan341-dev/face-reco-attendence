"""P2 tests: people, consent lifecycle, schedules, leave, isolation."""

import pytest

from apps.people.models import ConsentRecord, Person
from tests.conftest import tenant_ctx


@pytest.mark.django_db(transaction=True)
def test_person_crud_and_consent_lifecycle(auth, onboard):
    client, tokens = auth()
    created = client.post(
        "/api/people/",
        {"employee_id": "EMP-1", "first_name": "Asha", "last_name": "Kumar", "email": "asha@acme.test"},
        format="json",
    )
    assert created.status_code == 201, created.data
    person_id = created.data["id"]

    listing = client.get("/api/people/?search=asha")
    assert listing.status_code == 200 and len(listing.data) == 1

    grant = client.post(
        f"/api/people/{person_id}/consents/grant/",
        {"purpose": "biometric_attendance", "evidence": "Signed form"},
        format="json",
    )
    assert grant.status_code == 201, grant.data

    duplicate = client.post(
        f"/api/people/{person_id}/consents/grant/",
        {"purpose": "biometric_attendance"},
        format="json",
    )
    assert duplicate.status_code == 409

    withdraw = client.post(
        f"/api/people/{person_id}/consents/withdraw/",
        {"purpose": "biometric_attendance", "evidence": "Withdrawal request"},
        format="json",
    )
    assert withdraw.status_code == 200, withdraw.data

    consents = client.get(f"/api/people/{person_id}/consents/").data
    assert len(consents) == 2
    assert consents[0]["granted"] is False  # latest record is withdrawal

    with tenant_ctx(tokens["org_id"]):
        # Append-only: neither record was overwritten in place.
        assert ConsentRecord.objects.filter(person_id=person_id).count() == 2
        assert Person.objects.get(pk=person_id).status == "active"


@pytest.mark.django_db(transaction=True)
def test_overnight_shift_and_holiday(auth):
    client, _ = auth()
    created = client.post(
        "/api/shifts/",
        {"name": "Night", "start_time": "22:00:00", "end_time": "06:00:00", "grace_minutes": 10},
        format="json",
    )
    assert created.status_code == 201, created.data
    assert created.data["is_overnight"] is True

    holiday = client.post(
        "/api/holidays/", {"name": "New Year", "date": "2026-01-01"}, format="json"
    )
    assert holiday.status_code == 201, holiday.data
    listing = client.get("/api/holidays/?year=2026").data
    assert any(h["name"] == "New Year" for h in listing)


@pytest.mark.django_db(transaction=True)
def test_leave_request_decision_and_cross_tenant_hiding(auth, onboard):
    client, _ = auth()
    person = client.post(
        "/api/people/", {"first_name": "Ravi", "employee_id": "E-2"}, format="json"
    ).data

    request = client.post(
        "/api/leave-requests/",
        {
            "person": person["id"],
            "leave_type": "casual",
            "start_date": "2026-11-23",
            "end_date": "2026-11-24",
            "reason": "Personal",
        },
        format="json",
    )
    assert request.status_code == 201, request.data
    assert request.data["status"] == "pending"

    decision = client.post(
        f"/api/leave-requests/{request.data['id']}/decision/",
        {"decision": "approved"},
        format="json",
    )
    assert decision.status_code == 200 and decision.data["status"] == "approved"

    # Another tenant cannot see or decide this leave request.
    _, _, other_client = onboard("Globex", "globex", "owner@globex.test")
    assert all(item["id"] != request.data["id"] for item in other_client.get("/api/leave-requests/").data)
    denied = other_client.post(
        f"/api/leave-requests/{request.data['id']}/decision/", {"decision": "approved"}, format="json"
    )
    assert denied.status_code == 404


@pytest.mark.django_db(transaction=True)
def test_rls_blocks_cross_tenant_direct_orm_read(auth, onboard):
    client, _ = auth()
    client.post("/api/people/", {"first_name": "Secret", "employee_id": "SEC-1"}, format="json")
    _, _, other_client = onboard("Globex", "globex", "owner@globex.test")
    assert all(p["first_name"] != "Secret" for p in other_client.get("/api/people/").data)

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant', %s, true)", ["00000000-0000-0000-0000-000000000000"])
        cursor.execute("SELECT count(*) FROM people_person WHERE first_name = %s", ["Secret"])
        assert cursor.fetchone()[0] == 0
