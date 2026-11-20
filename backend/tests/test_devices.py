"""Device pairing, token auth, sync cursors and tenant isolation."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.devices.models import Device
from tests.conftest import tenant_ctx


def _pair(client, name: str = "Kiosk-1", kind: str = "terminal"):
    response = client.post(
        "/api/devices/pair/", {"name": name, "kind": kind}, format="json"
    )
    assert response.status_code == 201, response.data
    return response.data


def _device_client(token: str, device_id: str) -> APIClient:
    auth = APIClient()
    exchange = auth.post("/api/devices/auth/", {"token": token}, format="json")
    assert exchange.status_code == 200, exchange.data
    assert str(exchange.data["device_id"]) == str(device_id)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Device {exchange.data['access']}")
    return client


@pytest.mark.django_db(transaction=True)
def test_pair_auth_and_device_scoped_attendance(auth, onboard):
    client, tokens = auth()
    person = client.post(
        "/api/people/", {"first_name": "Kiosk", "employee_id": "K-1"}, format="json"
    ).data
    paired = _pair(client)
    assert "token" in paired
    assert "token_hash" not in paired

    device = _device_client(paired["token"], paired["id"])
    current = device.get("/api/devices/current/")
    assert current.status_code == 200, current.data
    assert str(current.data["id"]) == str(paired["id"])

    listing = client.get("/api/devices/")
    assert len(listing.data) == 1
    assert "token" not in listing.data[0]
    assert listing.data[0]["last_seen_at"] is not None

    from django.utils import timezone

    event = device.post(
        "/api/attendance/events/",
        {
            "person_id": person["id"],
            "event_type": "check_in",
            "occurred_at": timezone.now().isoformat(),
            "source": "web",
            "idempotency_key": "kiosk-1",
            "verification_status": "verified_device",
        },
        format="json",
    )
    assert event.status_code == 201, event.data
    assert event.data["source"] == "terminal"
    assert str(event.data["device"]) == str(paired["id"])

    _, _, other = onboard("Globex", "globex", "owner@globex.test")
    assert other.get("/api/devices/").data == []


@pytest.mark.django_db(transaction=True)
def test_rotate_and_deactivate_invalidate_devices(auth):
    client, _ = auth()
    paired = _pair(client, "Rotate")
    rotated = client.post(f"/api/devices/{paired['id']}/rotate/", {}, format="json")
    assert rotated.status_code == 200
    assert rotated.data["token"] != paired["token"]

    old_exchange = APIClient().post(
        "/api/devices/auth/", {"token": paired["token"]}, format="json"
    )
    assert old_exchange.status_code == 401

    deactivated = client.post(f"/api/devices/{paired['id']}/deactivate/", {}, format="json")
    assert deactivated.status_code == 200
    new_exchange = APIClient().post(
        "/api/devices/auth/", {"token": rotated.data["token"]}, format="json"
    )
    assert new_exchange.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_device_sync_cursor(auth):
    client, _ = auth()
    paired = _pair(client, "Cursor")
    device = _device_client(paired["token"], paired["id"])

    created = device.put(
        "/api/devices/current/sync-cursor/",
        {"last_event_id": "evt-42"},
        format="json",
    )
    assert created.status_code == 200, created.data
    assert created.data["last_event_id"] == "evt-42"

    fetched = device.get("/api/devices/current/sync-cursor/")
    assert fetched.status_code == 200
    assert fetched.data["last_event_id"] == "evt-42"

    with tenant_ctx("00000000-0000-0000-0000-000000000000"):
        assert Device.objects.filter(pk=paired["id"]).count() == 0
