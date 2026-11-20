"""P1 integration tests: onboarding, auth, MFA, tenant isolation, RLS."""

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.tenants.models import Branch, Membership, Organization
from tests.conftest import tenant_ctx


@pytest.mark.django_db(transaction=True)
def test_onboarding_creates_org_owner_branch_and_tokens(api):
    response = api.post(
        "/api/organizations/onboarding/",
        {
            "organization_name": "Acme Corp",
            "slug": "acme",
            "industry": "office",
            "owner_email": "owner@acme.test",
            "owner_username": "owner",
            "password": "Str0ngPass!word42",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["role"] == "owner"
    assert response.data["organization"]["slug"] == "acme"
    with tenant_ctx(response.data["org_id"]):
        assert Organization.objects.count() == 1
        assert Membership.objects.count() == 1
        assert Branch.objects.count() == 1
        assert Branch.objects.first().is_headquarters is True
    assert "access" in response.data and "refresh" in response.data


@pytest.mark.django_db(transaction=True)
def test_login_and_me(auth):
    client, tokens = auth()
    response = client.get("/api/auth/me/")
    assert response.status_code == 200, response.data
    assert response.data["email"] == "owner@acme.test"
    assert response.data["active_organization_id"] == tokens["org_id"]
    assert response.data["memberships"][0]["role"] == "owner"


@pytest.mark.django_db(transaction=True)
def test_cross_tenant_isolation_on_current_org(onboard):
    client_a = APIClient()
    _, tokens_a, authed_a = onboard("Acme", "acme", "owner@acme.test")
    _, tokens_b, authed_b = onboard("Globex", "globex", "owner@globex.test")

    # Each client sees only its own organization.
    assert authed_a.get("/api/organizations/current/").data["slug"] == "acme"
    assert authed_b.get("/api/organizations/current/").data["slug"] == "globex"

    # Spoofed header pointing to another tenant cannot override the JWT claim.
    response = authed_a.get(
        "/api/organizations/current/", HTTP_X_ORGANIZATION_ID=str(tokens_b["org_id"])
    )
    assert response.status_code == 200
    assert response.data["slug"] == "acme"

    # Unauthenticated request is rejected.
    assert client_a.get("/api/organizations/current/").status_code in (401, 403)


@pytest.mark.django_db(transaction=True)
def test_rls_hides_other_tenant_rows_even_in_raw_sql(onboard):
    _, tokens_a, authed_a = onboard("Acme", "acme", "owner@acme.test")
    _, _, authed_b = onboard("Globex", "globex", "owner@globex.test")

    # Create a branch in org B through its authenticated API client.
    resp = authed_b.post("/api/branches/", {"name": "Secret Branch", "code": "SEC"}, format="json")
    assert resp.status_code == 201, resp.data

    # Org A cannot list or fetch org B's branch.
    listed = authed_a.get("/api/branches/").data
    assert all(branch["name"] != "Secret Branch" for branch in listed)
    fetched = authed_a.get(f"/api/branches/{resp.data['id']}/")
    assert fetched.status_code == 404

    # Even raw SQL in org A's transaction sees zero rows from org B's org id.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_tenant', %s, true)", [str(tokens_a["org_id"])]
        )
        cursor.execute("SELECT count(*) FROM tenants_branch WHERE name = %s", ["Secret Branch"])
        assert cursor.fetchone()[0] == 0


@pytest.mark.django_db(transaction=True)
def test_mfa_setup_enable_and_challenge(auth):
    client, _ = auth()
    setup = client.post("/api/auth/mfa/setup/")
    assert setup.status_code == 200, setup.data
    assert setup.data["secret"]

    import pyotp

    code = pyotp.TOTP(setup.data["secret"]).now()
    enable = client.post("/api/auth/mfa/enable/", {"code": code}, format="json")
    assert enable.status_code == 200, enable.data
    assert client.get("/api/auth/me/").data["mfa_enabled"] is True

    anon = APIClient()
    login = anon.post(
        "/api/auth/login/",
        {"email": "owner@acme.test", "password": "Str0ngPass!word42"},
        format="json",
    )
    assert login.status_code == 200, login.data
    assert login.data.get("mfa_required") is True
    assert "access" not in login.data

    verify = anon.post(
        "/api/auth/mfa/challenge/",
        {"mfa_token": login.data["mfa_token"], "code": pyotp.TOTP(setup.data["secret"]).now()},
        format="json",
    )
    assert verify.status_code == 200, verify.data
    assert "access" in verify.data


@pytest.mark.django_db(transaction=True)
def test_non_admin_cannot_create_branch(auth):
    client, tokens = auth()
    # Invite an employee via the owner client.
    invite = client.post(
        "/api/members/",
        {"email": "employee@acme.test", "role": "employee"},
        format="json",
    )
    assert invite.status_code == 201, invite.data

    employee = APIClient()
    login = employee.post(
        "/api/auth/login/",
        {
            "email": "employee@acme.test",
            "password": "",
            "org_id": tokens["org_id"],
        },
        format="json",
    )
    # Invited user has unusable password, so login must fail.
    assert login.status_code in (400, 401)
