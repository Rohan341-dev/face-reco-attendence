from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.core.api import ContractAPIView
from apps.core.exceptions import error_response
from apps.core.permissions import IsActiveDevice, IsTenantHR, IsTenantMember
from apps.devices.authentication import DevicePrincipal

from .engine import AttendanceError, DuplicateEvent, IneligibleEvent, apply_correction, process_event
from .models import AttendanceEvent, AttendanceRecord, CorrectionRecord, MissingCheckoutAlert
from .serializers import (
    AttendanceEventInputSerializer,
    AttendanceEventSerializer,
    AttendanceRecordSerializer,
    CorrectionInputSerializer,
    CorrectionRecordSerializer,
    MissingCheckoutAlertSerializer,
    OfflineSyncSerializer,
)

CHANNEL_PERMISSIONS = [IsTenantMember | IsActiveDevice]


def _engine_error(exc: AttendanceError) -> Response:
    if isinstance(exc, DuplicateEvent):
        return error_response(str(exc), 409, exc.code)
    if isinstance(exc, IneligibleEvent):
        return error_response(str(exc), 422, exc.code)
    return error_response(str(exc), 400, exc.code)


def _event_input(request) -> dict:  # noqa: ANN001
    data = dict(request.data)
    user = request.user
    if isinstance(user, DevicePrincipal):
        data["device_id"] = str(user.device.id)
        data["source"] = AttendanceEvent.Source.TERMINAL
        if not data.get("branch_id") and user.device.branch_id:
            data["branch_id"] = str(user.device.branch_id)
    return data


class EventView(ContractAPIView):
    serializer_class = AttendanceEventSerializer
    permission_classes = CHANNEL_PERMISSIONS

    @extend_schema(responses=AttendanceEventSerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        qs = AttendanceEvent.objects.filter(organization_id=request.organization_id).select_related(
            "person", "branch"
        )
        for param, field in (
            ("person", "person_id"),
            ("event_type", "event_type"),
            ("verification_status", "verification_status"),
            ("source", "source"),
        ):
            value = request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(occurred_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(occurred_at__date__lte=date_to)
        return Response(AttendanceEventSerializer(qs.order_by("-occurred_at")[:200], many=True).data)

    @extend_schema(request=AttendanceEventInputSerializer)
    def post(self, request):  # noqa: ANN001, ANN201
        payload = AttendanceEventInputSerializer(data=_event_input(request))
        payload.is_valid(raise_exception=True)
        from .engine import EventInput

        data = EventInput(
            person_id=str(payload.validated_data["person_id"]),
            event_type=payload.validated_data["event_type"],
            occurred_at=payload.validated_data["occurred_at"],
            source=payload.validated_data["source"],
            idempotency_key=payload.validated_data["idempotency_key"],
            verification_status=payload.validated_data["verification_status"],
            verification_score=payload.validated_data.get("verification_score"),
            device_id=str(payload.validated_data["device_id"]) if payload.validated_data.get("device_id") else None,
            branch_id=str(payload.validated_data["branch_id"]) if payload.validated_data.get("branch_id") else None,
            metadata=payload.validated_data.get("metadata") or {},
        )
        try:
            event, created = process_event(request.organization_id, data)
        except AttendanceError as exc:
            return _engine_error(exc)
        return Response(
            AttendanceEventSerializer(event).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RecordListView(ContractAPIView):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsTenantMember]

    @extend_schema(responses=AttendanceRecordSerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        qs = AttendanceRecord.objects.filter(organization_id=request.organization_id).select_related(
            "person", "shift"
        )
        person = request.query_params.get("person")
        if person:
            qs = qs.filter(person_id=person)
        day_status = request.query_params.get("status")
        if day_status:
            qs = qs.filter(status=day_status)
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return Response(AttendanceRecordSerializer(qs.order_by("-date")[:200], many=True).data)


class CorrectionListCreateView(ContractAPIView):
    serializer_class = CorrectionRecordSerializer
    permission_classes = [IsTenantMember]

    @extend_schema(responses=CorrectionRecordSerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        qs = CorrectionRecord.objects.filter(organization_id=request.organization_id).order_by(
            "-applied_at"
        )
        return Response(CorrectionRecordSerializer(qs[:200], many=True).data)

    @extend_schema(request=CorrectionInputSerializer)
    def post(self, request):  # noqa: ANN001, ANN201
        if not IsTenantHR().has_permission(request, None):
            return error_response("HR or admin role required.", 403, "forbidden")
        payload = CorrectionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        values = payload.validated_data
        try:
            correction = apply_correction(
                request.organization_id,
                str(values["original_event"]),
                new_occurred_at=values["new_occurred_at"],
                new_event_type=values["new_event_type"],
                reason=values["reason"],
                corrected_by=request.user,
            )
        except AttendanceError as exc:
            return _engine_error(exc)
        return Response(CorrectionRecordSerializer(correction).data, status=status.HTTP_201_CREATED)


class MissingCheckoutListView(ContractAPIView):
    serializer_class = MissingCheckoutAlertSerializer
    permission_classes = [IsTenantMember]

    @extend_schema(responses=MissingCheckoutAlertSerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        qs = MissingCheckoutAlert.objects.filter(
            organization_id=request.organization_id
        ).select_related("person")
        resolved = request.query_params.get("resolved")
        if resolved in ("true", "false"):
            qs = qs.filter(resolved_at__isnull=resolved == "false")
        return Response(MissingCheckoutAlertSerializer(qs.order_by("-date")[:200], many=True).data)


class MissingCheckoutResolveView(ContractAPIView):
    serializer_class = MissingCheckoutAlertSerializer
    permission_classes = [IsTenantHR]

    def post(self, request, pk):  # noqa: ANN001, ANN201
        alert = MissingCheckoutAlert.objects.filter(
            pk=pk, organization_id=request.organization_id
        ).first()
        if alert is None:
            return error_response("Alert not found.", 404, "not_found")
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["resolved_at", "updated_at"])
        return Response(MissingCheckoutAlertSerializer(alert).data)


class OfflineSyncView(ContractAPIView):
    serializer_class = AttendanceEventSerializer
    permission_classes = CHANNEL_PERMISSIONS

    @extend_schema(request=OfflineSyncSerializer)
    def post(self, request):  # noqa: ANN001, ANN201
        payload = OfflineSyncSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        from .engine import EventInput

        results = []
        for item in payload.validated_data["events"]:
            raw = dict(item)
            if isinstance(request.user, DevicePrincipal):
                raw["device_id"] = str(request.user.device.id)
                raw["source"] = AttendanceEvent.Source.SYNC
            data = EventInput(
                person_id=str(raw["person_id"]),
                event_type=raw["event_type"],
                occurred_at=raw["occurred_at"],
                source=raw["source"],
                idempotency_key=raw["idempotency_key"],
                verification_status=raw["verification_status"],
                verification_score=raw.get("verification_score"),
                device_id=str(raw["device_id"]) if raw.get("device_id") else None,
                branch_id=str(raw["branch_id"]) if raw.get("branch_id") else None,
                metadata=raw.get("metadata") or {},
            )
            try:
                event, created = process_event(request.organization_id, data)
            except AttendanceError as exc:
                results.append(
                    {
                        "idempotency_key": data.idempotency_key,
                        "status": "rejected",
                        "code": exc.code,
                        "detail": str(exc),
                    }
                )
                continue
            results.append(
                {
                    "idempotency_key": data.idempotency_key,
                    "status": "accepted" if created else "duplicate",
                    "event_id": str(event.id),
                }
            )
        return Response({"results": results}, status=status.HTTP_207_MULTI_STATUS)
