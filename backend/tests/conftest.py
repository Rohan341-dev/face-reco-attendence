from contextlib import contextmanager

import pytest
from django.db import transaction
from rest_framework.test import APIClient

from apps.core.middleware import set_tenant


@contextmanager
def tenant_ctx(org_id):  # noqa: ANN001
    """Pin a tenant for direct ORM assertions in tests (RLS is enforced)."""
    with transaction.atomic():
        set_tenant(str(org_id))
        yield


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def onboard(api):
    """Register an organization and return (payload, tokens, client)."""
    def _onboard(name: str, slug: str, email: str):
        payload = {
            "organization_name": name,
            "slug": slug,
            "industry": "office",
            "timezone": "UTC",
            "owner_email": email,
            "owner_username": f"owner-{slug}-{email.split('@')[0]}",
            "password": "Str0ngPass!word42",
            "owner_first_name": "Owner",
            "owner_last_name": "User",
        }
        response = api.post("/api/organizations/onboarding/", payload, format="json")
        assert response.status_code == 201, response.data
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return payload, response.data, client
    return _onboard


@pytest.fixture
def auth(api, onboard):
    """Authenticate as the owner of a fresh organization."""
    def _auth(slug: str = "acme", email: str = "owner@acme.test"):
        _, tokens, client = onboard(f"Acme {slug}", slug, email)
        return client, tokens
    return _auth
