from __future__ import annotations

from rest_framework import serializers

from .models import AttendanceEvent, AttendanceRecord, CorrectionRecord, MissingCheckoutAlert


class AttendanceEventInputSerializer(serializers.Serializer):
    person_id = serializers.UUIDField()
    event_type = serializers.ChoiceField(choices=AttendanceEvent.EventType.choices)
    occurred_at = serializers.DateTimeField()
    source = serializers.ChoiceField(choices=AttendanceEvent.Source.choices)
    idempotency_key = serializers.CharField(max_length=120)
    verification_status = serializers.ChoiceField(
        choices=AttendanceEvent.Verification.choices,
        default=AttendanceEvent.Verification.PENDING,
    )
    verification_score = serializers.FloatField(required=False, allow_null=True, default=None)
    device_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    branch_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    metadata = serializers.JSONField(required=False, default=dict)


class AttendanceEventSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.get_full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True, default=None)

    class Meta:
        model = AttendanceEvent
        fields = [
            "id", "person", "person_name", "branch", "branch_name", "device",
            "event_type", "occurred_at", "received_at", "verification_status",
            "verification_score", "source", "idempotency_key", "metadata",
        ]
        read_only_fields = fields


class AttendanceRecordSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.get_full_name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True, default=None)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id", "person", "person_name", "branch", "date", "shift", "shift_name",
            "first_check_in", "last_check_out", "total_work_seconds",
            "total_break_seconds", "late_minutes", "early_minutes", "status",
            "flags", "computed_at",
        ]
        read_only_fields = fields


class CorrectionInputSerializer(serializers.Serializer):
    original_event = serializers.UUIDField()
    new_occurred_at = serializers.DateTimeField()
    new_event_type = serializers.ChoiceField(choices=AttendanceEvent.EventType.choices)
    reason = serializers.CharField(max_length=500)


class CorrectionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectionRecord
        fields = [
            "id", "original_event", "corrected_by", "reason", "new_occurred_at",
            "new_event_type", "applied_at",
        ]
        read_only_fields = fields


class MissingCheckoutAlertSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.get_full_name", read_only=True)

    class Meta:
        model = MissingCheckoutAlert
        fields = ["id", "person", "person_name", "date", "resolved_at", "created_at"]
        read_only_fields = fields


class OfflineSyncSerializer(serializers.Serializer):
    events = AttendanceEventInputSerializer(many=True)
