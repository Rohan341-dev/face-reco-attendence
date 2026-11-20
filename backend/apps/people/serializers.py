from __future__ import annotations

from rest_framework import serializers

from .models import BiometricTemplate, ConsentRecord, Employment, Person


class PersonSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True, default=None)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Person
        fields = [
            "id", "employee_id", "first_name", "last_name", "full_name",
            "email", "phone", "status", "branch", "branch_name",
            "department", "department_name", "user", "date_of_joining",
            "date_of_leaving", "created_at",
        ]
        read_only_fields = ["id", "full_name", "branch_name", "department_name", "created_at"]


class EmploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employment
        fields = ["id", "job_title", "employment_type", "manager", "created_at"]
        read_only_fields = ["id", "created_at"]


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = [
            "id", "purpose", "granted", "effective_at", "withdrawn_at",
            "evidence", "ip_address",
        ]
        read_only_fields = ["id", "purpose", "granted", "effective_at", "withdrawn_at", "evidence", "ip_address"]


class ConsentGrantSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=ConsentRecord.Purpose.choices)
    evidence = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class ConsentWithdrawSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=ConsentRecord.Purpose.choices)
    evidence = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class BiometricTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricTemplate
        fields = ["id", "person", "model_version", "is_active", "enrolled_at", "revoked_at"]
        read_only_fields = ["id", "model_version", "is_active", "enrolled_at", "revoked_at"]
