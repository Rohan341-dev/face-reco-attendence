from rest_framework import serializers

from .models import Holiday, LeaveRequest, Shift, WorkSchedule


class ShiftSerializer(serializers.ModelSerializer):
    is_overnight = serializers.BooleanField(read_only=True)

    class Meta:
        model = Shift
        fields = [
            "id", "name", "start_time", "end_time", "is_overnight",
            "break_minutes", "grace_minutes", "is_active", "created_at",
        ]
        read_only_fields = ["id", "is_overnight", "created_at"]


class WorkScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = [
            "id", "person", "shift", "effective_from", "effective_to",
            "days_of_week", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "name", "date", "is_working_day", "created_at"]
        read_only_fields = ["id", "created_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.full_name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "person", "person_name", "leave_type", "start_date", "end_date",
            "reason", "status", "decided_by", "decided_at", "created_at",
        ]
        read_only_fields = [
            "id", "person_name", "status", "decided_by", "decided_at", "created_at",
        ]

    def validate(self, attrs):  # noqa: ANN001
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "Cannot precede start date."})
        return attrs
