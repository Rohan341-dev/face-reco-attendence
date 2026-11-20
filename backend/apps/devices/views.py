from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.api import ContractAPIView
from apps.core.audit import log_action
from apps.core.exceptions import error_response
from apps.core.middleware import set_guc
from apps.core.permissions import IsActiveDevice, IsTenantAdmin, IsTenantHR, IsTenantMember
from apps.core.rls import PLATFORM_GUC

from .models import Device, DeviceSyncCursor
from .serializers import (
    DeviceAuthResponseSerializer,
    DeviceAuthSerializer,
    DevicePairSerializer,
    DeviceSerializer,
    SyncCursorSerializer,
    SyncCursorUpdateSerializer,
)
from .tokens import issue_device_token


class DevicePairView(ContractAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [IsTenantHR]

    @extend_schema(request=DevicePairSerializer)
    def post(self, request):  # noqa: ANN001, ANN201
        payload = DevicePairSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        token = Device.issue_token()
        device = Device.objects.create(
            organization_id=request.organization_id,
            name=payload.validated_data["name"],
            kind=payload.validated_data["kind"],
            branch_id=payload.validated_data.get("branch"),
            token_hash=Device.hash_token(token),
            paired_at=timezone.now(),
        )
        log_action(
            "device_auth",
            organization_id=request.organization_id,
            actor=request.user,
            object_repr=f"device:{device.id}",
            changes={"action": "paired", "kind": device.kind},
            request=request,
        )
        return Response(
            {**DeviceSerializer(device).data, "token": token},
            status=status.HTTP_201_CREATED,
        )


class DeviceListView(ContractAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [IsTenantMember]

    def get(self, request):  # noqa: ANN001, ANN201
        qs = Device.objects.filter(organization_id=request.organization_id).select_related("branch")
        active = request.query_params.get("active")
        if active in ("true", "false"):
            qs = qs.filter(is_active=active == "true")
        return Response(DeviceSerializer(qs.order_by("name"), many=True).data)


class DeviceRotateView(ContractAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [IsTenantAdmin]

    def post(self, request, pk):  # noqa: ANN001, ANN201
        device = Device.objects.filter(pk=pk, organization_id=request.organization_id).first()
        if device is None:
            return error_response("Device not found.", 404, "not_found")
        token = Device.issue_token()
        device.token_hash = Device.hash_token(token)
        device.save(update_fields=["token_hash", "updated_at"])
        log_action(
            "device_auth",
            organization_id=request.organization_id,
            actor=request.user,
            object_repr=f"device:{device.id}",
            changes={"action": "token_rotated"},
            request=request,
        )
        return Response({"token": token})


class DeviceDeactivateView(ContractAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [IsTenantAdmin]

    def post(self, request, pk):  # noqa: ANN001, ANN201
        device = Device.objects.filter(pk=pk, organization_id=request.organization_id).first()
        if device is None:
            return error_response("Device not found.", 404, "not_found")
        device.is_active = False
        device.save(update_fields=["is_active", "updated_at"])
        log_action(
            "device_revoked",
            organization_id=request.organization_id,
            actor=request.user,
            object_repr=f"device:{device.id}",
            request=request,
        )
        return Response(DeviceSerializer(device).data)


class DeviceAuthView(ContractAPIView):
    serializer_class = DeviceAuthResponseSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=DeviceAuthSerializer)
    def post(self, request):  # noqa: ANN001, ANN201
        payload = DeviceAuthSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        token_hash = Device.hash_token(payload.validated_data["token"])
        # Token exchange is the one pre-tenant lookup: it runs under the
        # audited platform scope because no org context exists yet.
        with transaction.atomic():
            set_guc(PLATFORM_GUC, "on")
            device = Device.objects.filter(token_hash=token_hash, is_active=True).first()
            if device is None:
                log_action(
                    "login_failed",
                    object_repr="device-token",
                    actor_label="device",
                    request=request,
                )
        if device is None:
            return error_response("Invalid device token.", 401, "invalid_device_token")
        return Response(
            {
                "access": issue_device_token(device),
                "device_id": str(device.id),
                "organization_id": str(device.organization_id),
                "expires_in": 3600,
            }
        )


class CurrentDeviceView(ContractAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [IsActiveDevice]

    def get(self, request):  # noqa: ANN001, ANN201
        device = request.user.device
        return Response(DeviceSerializer(device).data)


class SyncCursorView(ContractAPIView):
    serializer_class = SyncCursorSerializer
    permission_classes = [IsActiveDevice]

    def get(self, request):  # noqa: ANN001, ANN201
        device = request.user.device
        cursor = DeviceSyncCursor.objects.filter(device=device, organization_id=device.organization_id).first()
        if cursor is None:
            return Response(
                {
                    "device": str(device.id),
                    "last_synced_at": None,
                    "last_event_id": "",
                }
            )
        return Response(SyncCursorSerializer(cursor).data)

    @extend_schema(request=SyncCursorUpdateSerializer)
    def put(self, request):  # noqa: ANN001, ANN201
        device = request.user.device
        payload = SyncCursorUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cursor, _ = DeviceSyncCursor.objects.get_or_create(
            device=device, organization_id=device.organization_id
        )
        if "last_synced_at" in payload.validated_data:
            cursor.last_synced_at = payload.validated_data["last_synced_at"]
        else:
            cursor.last_synced_at = timezone.now()
        cursor.last_event_id = payload.validated_data.get("last_event_id", "")
        cursor.save(update_fields=["last_synced_at", "last_event_id", "updated_at"])
        return Response(SyncCursorSerializer(cursor).data)
