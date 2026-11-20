"""Shared DRF permission helpers."""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.tenants.models import Membership


class IsTenantMember(BasePermission):
    """Requires an authenticated user with an active membership in the
    resolved organization context (set by TenantContextMiddleware)."""

    message = "An active membership in this organization is required."

    def has_permission(self, request, view):
        user = request.user
        org_id = getattr(request, "organization_id", None)
        if not user or not user.is_authenticated or not org_id:
            return False
        return Membership.objects.filter(
            user_id=user.id, organization_id=org_id, is_active=True
        ).exists()


class IsTenantHR(IsTenantMember):
    message = "HR role required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return Membership.objects.filter(
            user_id=request.user.id,
            organization_id=request.organization_id,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN, Membership.Role.HR],
            is_active=True,
        ).exists()


class IsTenantAdmin(IsTenantMember):
    message = "Organization admin role required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return Membership.objects.filter(
            user_id=request.user.id,
            organization_id=request.organization_id,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
            is_active=True,
        ).exists()


class IsPlatformAdmin(BasePermission):
    message = "Platform administrator required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_platform_admin", False)
        )


class IsTenantMemberOrReadOnly(IsTenantMember):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return super().has_permission(request, view)
