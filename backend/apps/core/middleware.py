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
from contextlib import contextmanager

from django.db import connection, transaction
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from apps.core.rls import DEVICE_GUC, PLATFORM_GUC, TENANT_GUC, USER_GUC

logger = logging.getLogger(__name__)


def set_guc(name: str, value: str | None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [name, value or ""])


def set_tenant(tenant_id: str | None) -> None:
    set_guc(TENANT_GUC, tenant_id)


@contextmanager
def tenant_context(
    tenant_id: str | None,
    *,
    user_id=None,  # noqa: ANN001
    device_id=None,  # noqa: ANN001
    platform_admin: bool = False,
):
    """Pin tenant GUCs for work outside an HTTP request (Celery, consumers).

    The atomic block scopes ``SET LOCAL`` to the surrounding unit of work so
    RLS applies to every query, including raw SQL.
    """
    with transaction.atomic():
        set_guc(USER_GUC, str(user_id) if user_id else None)
        set_guc(DEVICE_GUC, str(device_id) if device_id else None)
        set_guc(PLATFORM_GUC, "on" if platform_admin else None)
        set_tenant(tenant_id)
        yield


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
            request.device_id = claims.get("device_id")
            if org_id:
                set_tenant(org_id)
            else:
                set_tenant(None)
            set_guc(DEVICE_GUC, request.device_id)

            return self.get_response(request)

    def _authenticate(self, request):  # noqa: ANN001
        header = self.jwt_auth.get_header(request)
        if header:
            try:
                raw = self.jwt_auth.get_raw_token(header)
                token = self.jwt_auth.get_validated_token(raw)
                user = self.jwt_auth.get_user(token)
                return user, dict(token.payload)
            except (InvalidToken, TokenError):
                pass

        # Device tokens are signed with the same secret but are not user tokens.
        parts = request.META.get("HTTP_AUTHORIZATION", "").split()
        if len(parts) == 2 and parts[0] == "Device":
            from apps.devices.authentication import DevicePrincipal
            from apps.devices.models import Device
            from apps.devices.tokens import decode_device_token

            payload = decode_device_token(parts[1])
            if payload:
                # SET LOCAL needs a transaction; pin the tenant before the
                # RLS-protected device lookup, then carry the claims onward.
                with transaction.atomic():
                    set_tenant(payload["org_id"])
                    device = Device.objects.filter(
                        pk=payload["device_id"], organization_id=payload["org_id"], is_active=True
                    ).first()
                if device:
                    return DevicePrincipal(device), payload
        return None, {}

    def _resolve_org(self, request, user, claims):  # noqa: ANN001, ANN003
        org_id = claims.get("org_id") or request.headers.get("X-Organization-ID")
        if org_id is None or user is None:
            return None

        if claims.get("device_id"):
            from apps.devices.models import Device

            return (
                org_id
                if Device.objects.filter(
                    pk=claims["device_id"], organization_id=org_id, is_active=True
                ).exists()
                else None
            )

        from apps.tenants.models import Membership  # local import to avoid app-load cycles

        if not Membership.objects.filter(
            user_id=user.id, organization_id=org_id, is_active=True
        ).exists():
            logger.warning(
                "Rejected tenant context org=%s user=%s (no active membership)", org_id, user.id
            )
            return None
        return org_id
