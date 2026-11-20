"""Tenant context middleware.

Resolves the active organization for the request (JWT ``org_id`` claim or
``X-Organization-ID`` header), verifies the user holds an active membership,
and pins it to the database connection via ``app.current_tenant`` so that
PostgreSQL Row-Level Security policies apply to every query in the request.

``app.current_user`` is pinned first so that RLS policies which need to read
the user's memberships (before the tenant is known) can evaluate them.

The view executes inside an atomic block so that ``SET LOCAL`` applies to
all ORM queries, including raw SQL.
"""

from __future__ import annotations

import logging

from django.db import connection, transaction
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from apps.core.rls import PLATFORM_GUC, TENANT_GUC, USER_GUC

logger = logging.getLogger(__name__)


def set_guc(name: str, value: str | None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [name, value or ""])


def set_tenant(tenant_id: str | None) -> None:
    set_guc(TENANT_GUC, tenant_id)


class TenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        user, claims = self._authenticate(request)
        request.tenant_user = user
        request.jwt_claims = claims

        with transaction.atomic():
            set_guc(USER_GUC, str(user.id) if user else None)
            set_guc(PLATFORM_GUC, "on" if (claims.get("platform_admin") and not claims.get("org_id")) else None)

            org_id = self._resolve_org(request, user, claims)
            request.organization_id = org_id
            if org_id:
                set_tenant(org_id)
            else:
                set_tenant(None)

            return self.get_response(request)

    def _authenticate(self, request):  # noqa: ANN001
        header = self.jwt_auth.get_header(request)
        if not header:
            return None, {}
        try:
            raw = self.jwt_auth.get_raw_token(header)
            token = self.jwt_auth.get_validated_token(raw)
            user = self.jwt_auth.get_user(token)
            return user, dict(token.payload)
        except (InvalidToken, TokenError):
            return None, {}

    def _resolve_org(self, request, user, claims):  # noqa: ANN001, ANN003
        org_id = claims.get("org_id") or request.headers.get("X-Organization-ID")
        if org_id is None or user is None:
            return None

        from apps.tenants.models import Membership  # local import to avoid app-load cycles

        if not Membership.objects.filter(
            user_id=user.id, organization_id=org_id, is_active=True
        ).exists():
            logger.warning(
                "Rejected tenant context org=%s user=%s (no active membership)", org_id, user.id
            )
            return None
        return org_id
