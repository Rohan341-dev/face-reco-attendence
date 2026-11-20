from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.core.api import ContractAPIView
from apps.core.exceptions import error_response
from apps.core.permissions import IsTenantAdmin, IsTenantHR, IsTenantMember

from .models import Holiday, LeaveRequest, Shift, WorkSchedule
from .serializers import HolidaySerializer, LeaveRequestSerializer, ShiftSerializer, WorkScheduleSerializer


class ShiftListCreateView(ContractAPIView):
    serializer_class = ShiftSerializer

    permission_classes = [IsTenantMember]

    @extend_schema(responses=ShiftSerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        qs = Shift.objects.filter(organization_id=request.organization_id, is_active=True).order_by("start_time", "name")
        return Response(ShiftSerializer(qs, many=True).data)

    def post(self, request):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        serializer = ShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shift = serializer.save(organization_id=request.organization_id)
        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


class ShiftDetailView(ContractAPIView):
    serializer_class = ShiftSerializer

    permission_classes = [IsTenantMember]

    def _get(self, request, pk):  # noqa: ANN001
        return Shift.objects.filter(pk=pk, organization_id=request.organization_id).first()

    def patch(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        shift = self._get(request, pk)
        if not shift:
            return error_response("Shift not found.", 404, "not_found")
        serializer = ShiftSerializer(shift, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        shift = self._get(request, pk)
        if not shift:
            return error_response("Shift not found.", 404, "not_found")
        shift.is_active = False
        shift.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkScheduleListCreateView(ContractAPIView):
    serializer_class = WorkScheduleSerializer

    permission_classes = [IsTenantMember]

    @extend_schema(responses=WorkScheduleSerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        qs = WorkSchedule.objects.filter(organization_id=request.organization_id)
        person = request.query_params.get("person")
        if person:
            qs = qs.filter(person_id=person)
        return Response(WorkScheduleSerializer(qs.select_related("shift"), many=True).data)

    def post(self, request):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        serializer = WorkScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save(organization_id=request.organization_id)
        return Response(WorkScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED)


class WorkScheduleDetailView(ContractAPIView):
    serializer_class = WorkScheduleSerializer

    permission_classes = [IsTenantMember]

    def delete(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        schedule = WorkSchedule.objects.filter(pk=pk, organization_id=request.organization_id).first()
        if not schedule:
            return error_response("Assignment not found.", 404, "not_found")
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HolidayListCreateView(ContractAPIView):
    serializer_class = HolidaySerializer

    permission_classes = [IsTenantMember]

    @extend_schema(responses=HolidaySerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        qs = Holiday.objects.filter(organization_id=request.organization_id).order_by("date")
        year = request.query_params.get("year")
        if year and year.isdigit():
            qs = qs.filter(date__year=int(year))
        return Response(HolidaySerializer(qs, many=True).data)

    def post(self, request):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        serializer = HolidaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        holiday = serializer.save(organization_id=request.organization_id)
        return Response(HolidaySerializer(holiday).data, status=status.HTTP_201_CREATED)


class HolidayDetailView(ContractAPIView):
    serializer_class = HolidaySerializer

    permission_classes = [IsTenantMember]

    def delete(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        holiday = Holiday.objects.filter(pk=pk, organization_id=request.organization_id).first()
        if not holiday:
            return error_response("Holiday not found.", 404, "not_found")
        holiday.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaveRequestListCreateView(ContractAPIView):
    serializer_class = LeaveRequestSerializer

    permission_classes = [IsTenantMember]

    @extend_schema(responses=LeaveRequestSerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        qs = LeaveRequest.objects.filter(organization_id=request.organization_id).select_related("person")
        person = request.query_params.get("person")
        if person:
            qs = qs.filter(person_id=person)
        leave_status = request.query_params.get("status")
        if leave_status:
            qs = qs.filter(status=leave_status)
        return Response(LeaveRequestSerializer(qs.order_by("-created_at"), many=True).data)

    def post(self, request):  # noqa: ANN001, ANN201
        from apps.people.models import Person

        person_id = request.data.get("person")
        if not person_id:
            own = Person.objects.filter(
                organization_id=request.organization_id, user_id=request.user.id
            ).first()
            if not own:
                return error_response("No person profile linked to your account.", 400, "no_profile")
            person_id = str(own.id)
        elif not (
            IsTenantAdmin().has_permission(request, None)
            or IsTenantHR().has_permission(request, None)
        ):
            return error_response("You can only submit leave for yourself.", 403, "forbidden")

        if not Person.objects.filter(pk=person_id, organization_id=request.organization_id).exists():
            return error_response("Person not found in this organization.", 404, "not_found")

        serializer = LeaveRequestSerializer(data={**request.data, "person": person_id})
        serializer.is_valid(raise_exception=True)
        leave = serializer.save(organization_id=request.organization_id)
        return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)


class LeaveRequestDecisionView(ContractAPIView):
    serializer_class = LeaveRequestSerializer

    permission_classes = [IsTenantMember]

    def post(self, request, pk):  # noqa: ANN001, ANN201
        if not (IsTenantAdmin().has_permission(request, None) or IsTenantHR().has_permission(request, None)):
            return error_response("HR or admin role required.", 403, "forbidden")
        leave = LeaveRequest.objects.filter(pk=pk, organization_id=request.organization_id).first()
        if not leave:
            return error_response("Leave request not found.", 404, "not_found")
        if leave.status != LeaveRequest.Status.PENDING:
            return error_response("Leave request already decided.", 409, "already_decided")
        decision = request.data.get("decision")
        if decision not in ("approved", "rejected"):
            return error_response("decision must be 'approved' or 'rejected'.", 400, "invalid_decision")
        leave.status = decision
        leave.decided_by = request.user
        leave.decided_at = timezone.now()
        leave.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
        return Response(LeaveRequestSerializer(leave).data)
