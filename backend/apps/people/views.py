from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.core.api import ContractAPIView
from apps.core.audit import client_ip, log_action
from apps.core.exceptions import error_response
from apps.core.permissions import IsTenantAdmin, IsTenantMember

from .models import ConsentRecord, Employment, Person, has_active_consent
from .serializers import (
    BiometricTemplateSerializer,
    ConsentGrantSerializer,
    ConsentRecordSerializer,
    ConsentWithdrawSerializer,
    EmploymentSerializer,
    PersonSerializer,
)


class PersonListCreateView(ContractAPIView):
    serializer_class = PersonSerializer

    permission_classes = [IsTenantMember]

    @extend_schema(responses=PersonSerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        qs = Person.objects.filter(organization_id=request.organization_id).select_related(
            "branch", "department"
        )
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(first_name__icontains=search) | qs.filter(last_name__icontains=search)
        branch = request.query_params.get("branch")
        if branch:
            qs = qs.filter(branch_id=branch)
        department = request.query_params.get("department")
        if department:
            qs = qs.filter(department_id=department)
        person_status = request.query_params.get("status")
        if person_status:
            qs = qs.filter(status=person_status)
        qs = qs.order_by("last_name", "first_name")
        return Response(PersonSerializer(qs, many=True).data)

    def post(self, request):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        serializer = PersonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        person = serializer.save(organization_id=request.organization_id)
        Employment.objects.create(organization_id=request.organization_id, person=person)
        return Response(PersonSerializer(person).data, status=status.HTTP_201_CREATED)


class PersonDetailView(ContractAPIView):
    serializer_class = PersonSerializer

    permission_classes = [IsTenantMember]

    def _get(self, request, pk):  # noqa: ANN001
        return Person.objects.filter(pk=pk, organization_id=request.organization_id).first()

    def get(self, request, pk):  # noqa: ANN001, ANN201
        person = self._get(request, pk)
        if not person:
            return error_response("Person not found.", 404, "not_found")
        return Response(PersonSerializer(person).data)

    def patch(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        person = self._get(request, pk)
        if not person:
            return error_response("Person not found.", 404, "not_found")
        serializer = PersonSerializer(person, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        person = self._get(request, pk)
        if not person:
            return error_response("Person not found.", 404, "not_found")
        person.status = Person.Status.INACTIVE
        person.save(update_fields=["status", "updated_at"])
        # Revoking active consent is mandatory when a person is deactivated;
        # the revocation is an appended record, never an in-place update.
        latest_by_purpose: dict[str, ConsentRecord] = {}
        for record in ConsentRecord.objects.filter(
            organization_id=request.organization_id, person=person
        ).order_by("effective_at"):
            latest_by_purpose[record.purpose] = record
        for purpose, record in latest_by_purpose.items():
            if record.granted:
                ConsentRecord.objects.create(
                    organization_id=request.organization_id,
                    person=person,
                    purpose=purpose,
                    granted=False,
                    withdrawn_at=timezone.now(),
                    evidence="Person deactivated",
                )
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmploymentView(ContractAPIView):
    serializer_class = EmploymentSerializer

    permission_classes = [IsTenantMember]

    def get(self, request, person_id):  # noqa: ANN001, ANN201
        employment = Employment.objects.filter(
            person_id=person_id, organization_id=request.organization_id
        ).first()
        if not employment:
            return error_response("Employment record not found.", 404, "not_found")
        return Response(EmploymentSerializer(employment).data)

    def patch(self, request, person_id):  # noqa: ANN001, ANN201
        if not IsTenantAdmin().has_permission(request, None):
            return error_response("Admin role required.", 403, "forbidden")
        employment = Employment.objects.filter(
            person_id=person_id, organization_id=request.organization_id
        ).first()
        if not employment:
            return error_response("Employment record not found.", 404, "not_found")
        serializer = EmploymentSerializer(employment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ConsentView(ContractAPIView):
    serializer_class = ConsentRecordSerializer

    permission_classes = [IsTenantMember]

    @extend_schema(responses=ConsentRecordSerializer(many=True))
    def get(self, request, person_id):  # noqa: ANN001, ANN201
        records = ConsentRecord.objects.filter(
            person_id=person_id, organization_id=request.organization_id
        ).order_by("-effective_at")
        return Response(ConsentRecordSerializer(records, many=True).data)


class ConsentGrantView(ContractAPIView):
    serializer_class = ConsentRecordSerializer

    permission_classes = [IsTenantMember]

    @extend_schema(request=ConsentGrantSerializer)
    def post(self, request, person_id):  # noqa: ANN001, ANN201
        with transaction.atomic():
            purpose = request.data.get("purpose")
            serializer = ConsentGrantSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if has_active_consent(request.organization_id, person_id, purpose):
                return error_response("Consent already granted for this purpose.", 409, "already_granted")
            record = ConsentRecord.objects.create(
                organization_id=request.organization_id,
                person_id=person_id,
                purpose=purpose,
                granted=True,
                evidence=serializer.validated_data["evidence"],
                ip_address=client_ip(request),
            )
            log_action(
                "consent_granted",
                organization_id=request.organization_id,
                actor=request.user,
                object_repr=f"person:{person_id} purpose:{purpose}",
                request=request,
            )
        return Response(ConsentRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class ConsentWithdrawView(ContractAPIView):
    serializer_class = ConsentRecordSerializer

    permission_classes = [IsTenantMember]

    @extend_schema(request=ConsentWithdrawSerializer)
    def post(self, request, person_id):  # noqa: ANN001, ANN201
        with transaction.atomic():
            serializer = ConsentWithdrawSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            purpose = serializer.validated_data["purpose"]
            if not has_active_consent(request.organization_id, person_id, purpose):
                return error_response("No active consent for this purpose.", 404, "no_active_consent")
            # Withdrawal is recorded as an appended evidence row, never an in-place update.
            record = ConsentRecord.objects.create(
                organization_id=request.organization_id,
                person_id=person_id,
                purpose=purpose,
                granted=False,
                withdrawn_at=timezone.now(),
                evidence=serializer.validated_data["evidence"],
                ip_address=client_ip(request),
            )
            log_action(
                "consent_withdrawn",
                organization_id=request.organization_id,
                actor=request.user,
                object_repr=f"person:{person_id} purpose:{purpose}",
                request=request,
            )
        return Response(ConsentRecordSerializer(record).data)


class BiometricTemplateListView(ContractAPIView):
    serializer_class = BiometricTemplateSerializer

    permission_classes = [IsTenantMember]

    @extend_schema(responses=BiometricTemplateSerializer(many=True))
    def get(self, request):  # noqa: ANN001, ANN201
        from .models import BiometricTemplate

        qs = BiometricTemplate.objects.filter(organization_id=request.organization_id, is_active=True)
        person = request.query_params.get("person")
        if person:
            qs = qs.filter(person_id=person)
        return Response(BiometricTemplateSerializer(qs, many=True).data)
