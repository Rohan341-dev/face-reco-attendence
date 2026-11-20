from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import FaceTrackTokenObtainPairSerializer, _membership_claims
from apps.core.audit import log_action
from apps.core.middleware import set_tenant
from apps.core.permissions import IsPlatformAdmin, IsTenantAdmin, IsTenantMember
from .models import Branch, Department, Membership, Organization, OrganizationSettings
from .serializers import (
    BranchSerializer,
    DepartmentSerializer,
    InviteMemberSerializer,
    MembershipSerializer,
    OnboardingSerializer,
    OrganizationSerializer,
    OrganizationSettingsSerializer,
)


class OnboardingView(APIView):
    """Public self-serve registration: owner account + organization."""

    permission_classes = [AllowAny]
    throttle_scope = "anon"

    @extend_schema(request=OnboardingSerializer)
    def post(self, request):  # noqa: ANN001, ANN201
        serializer = OnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            result = serializer.create(serializer.validated_data)
            org = result["organization"]
            owner = result["owner"]
            # serializer.create already pinned the new tenant for child rows;
            # re-pin for the remainder of this view transaction.
            set_tenant(str(org.id))
            refresh = RefreshToken.for_user(owner)
            org_id, role = _membership_claims(owner, str(org.id))
            refresh["org_id"] = org_id
            refresh["role"] = role
            refresh["platform_admin"] = False
            refresh["mfa_pending"] = False
            log_action(
                "other",
                organization_id=org.id,
                actor=owner,
                object_repr=f"organization:{org.slug}",
                changes={"event": "onboarding", "name": org.name},
                request=request,
            )
        return Response(
            {
                "organization": OrganizationSerializer(org).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "org_id": org_id,
                "role": role,
            },
            status=status.HTTP_201_CREATED,
        )


class CurrentOrganizationView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):  # noqa: ANN001, ANN201
        org = Organization.objects.get(pk=request.organization_id)
        membership = Membership.objects.get(
            user=request.user, organization_id=request.organization_id, is_active=True
        )
        data = OrganizationSerializer(org).data
        data["role"] = membership.role
        return Response(data)


class OrganizationSettingsView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):  # noqa: ANN001, ANN201
        settings_obj, _ = OrganizationSettings.objects.get_or_create(
            organization_id=request.organization_id
        )
        return Response(OrganizationSettingsSerializer(settings_obj).data)

    def patch(self, request):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return Response({"error": {"detail": "Admin role required."}}, status=403)
        settings_obj, _ = OrganizationSettings.objects.get_or_create(
            organization_id=request.organization_id
        )
        serializer = OrganizationSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BranchListCreateView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):  # noqa: ANN001, ANN201
        qs = Branch.objects.filter(organization_id=request.organization_id).order_by("-is_headquarters", "name")
        return Response(BranchSerializer(qs, many=True).data)

    def post(self, request):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return Response({"error": {"detail": "Admin role required."}}, status=403)
        serializer = BranchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization_id=request.organization_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BranchDetailView(APIView):
    permission_classes = [IsTenantMember]

    def _get(self, request, pk):  # noqa: ANN001
        return Branch.objects.filter(pk=pk, organization_id=request.organization_id).first()

    def get(self, request, pk):  # noqa: ANN001, ANN201
        branch = self._get(request, pk)
        if not branch:
            return Response({"error": {"detail": "Not found."}}, status=404)
        return Response(BranchSerializer(branch).data)

    def patch(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return Response({"error": {"detail": "Admin role required."}}, status=403)
        branch = self._get(request, pk)
        if not branch:
            return Response({"error": {"detail": "Not found."}}, status=404)
        serializer = BranchSerializer(branch, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return Response({"error": {"detail": "Admin role required."}}, status=403)
        branch = self._get(request, pk)
        if not branch:
            return Response({"error": {"detail": "Not found."}}, status=404)
        branch.is_active = False
        branch.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class DepartmentListCreateView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):  # noqa: ANN001, ANN201
        qs = Department.objects.filter(organization_id=request.organization_id).order_by("name")
        return Response(DepartmentSerializer(qs, many=True).data)

    def post(self, request):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return Response({"error": {"detail": "Admin role required."}}, status=403)
        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization_id=request.organization_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MemberListInviteView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):  # noqa: ANN001, ANN201
        qs = (
            Membership.objects.filter(organization_id=request.organization_id, is_active=True)
            .select_related("user")
            .order_by("role", "user__email")
        )
        return Response(MembershipSerializer(qs, many=True).data)

    @extend_schema(request=InviteMemberSerializer)
    def post(self, request):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return Response({"error": {"detail": "Admin role required."}}, status=403)
        serializer = InviteMemberSerializer(
            data=request.data, context={"organization_id": request.organization_id}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.create(serializer.validated_data)
        log_action(
            "member_added",
            organization_id=request.organization_id,
            actor=request.user,
            object_repr=f"user:{result['membership'].user_id}",
            changes={"role": result["membership"].role},
            request=request,
        )
        return Response(MembershipSerializer(result["membership"]).data, status=status.HTTP_201_CREATED)


class MemberDetailView(APIView):
    permission_classes = [IsTenantMember]

    def _get(self, request, pk):  # noqa: ANN001
        return Membership.objects.filter(
            pk=pk, organization_id=request.organization_id, is_active=True
        ).first()

    def patch(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return Response({"error": {"detail": "Admin role required."}}, status=403)
        membership = self._get(request, pk)
        if not membership:
            return Response({"error": {"detail": "Not found."}}, status=404)
        serializer = MembershipSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        old_role = membership.role
        serializer.save()
        if membership.role != old_role:
            log_action(
                "member_role_changed",
                organization_id=request.organization_id,
                actor=request.user,
                object_repr=f"user:{membership.user_id}",
                changes={"old_role": old_role, "new_role": membership.role},
                request=request,
            )
        return Response(serializer.data)

    def delete(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return Response({"error": {"detail": "Admin role required."}}, status=403)
        membership = self._get(request, pk)
        if not membership:
            return Response({"error": {"detail": "Not found."}}, status=404)
        if membership.user_id == request.user.id:
            return Response(
                {"error": {"detail": "You cannot remove your own membership."}}, status=400
            )
        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])
        log_action(
            "member_removed",
            organization_id=request.organization_id,
            actor=request.user,
            object_repr=f"user:{membership.user_id}",
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformOrganizationListView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):  # noqa: ANN001, ANN201
        qs = Organization.objects.all().order_by("-created_at")
        return Response(OrganizationSerializer(qs, many=True).data)


class PlatformOrganizationActionView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):  # noqa: ANN001, ANN201
        action = request.data.get("action")
        org = Organization.objects.filter(pk=pk).first()
        if not org:
            return Response({"error": {"detail": "Not found."}}, status=404)
        if action == "suspend":
            org.is_active = False
            org.suspended_at = timezone.now()
            log_action("other", organization_id=org.id, actor=request.user,
                       object_repr=f"organization:{org.slug}",
                       changes={"event": "suspend"}, request=request)
        elif action == "activate":
            org.is_active = True
            org.suspended_at = None
            log_action("other", organization_id=org.id, actor=request.user,
                       object_repr=f"organization:{org.slug}",
                       changes={"event": "activate"}, request=request)
        else:
            return Response({"error": {"detail": "Unknown action."}}, status=400)
        org.save(update_fields=["is_active", "suspended_at", "updated_at"])
        return Response(OrganizationSerializer(org).data)
