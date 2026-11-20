from __future__ import annotations

from rest_framework import serializers

from .models import Device, DeviceSyncCursor


class DevicePairSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    kind = serializers.ChoiceField(choices=Device.Kind.choices, default=Device.Kind.TERMINAL)
    branch = serializers.UUIDField(required=False, allow_null=True, default=None)


class DeviceSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True, default=None)

    class Meta:
        model = Device
        fields = [
            "id", "name", "kind", "branch", "branch_name", "is_active",
            "paired_at", "last_seen_at", "created_at",
        ]
        read_only_fields = fields


class DeviceAuthSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=200)


class DeviceAuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    device_id = serializers.UUIDField()
    organization_id = serializers.UUIDField()
    expires_in = serializers.IntegerField()


class SyncCursorSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceSyncCursor
        fields = ["id", "device", "last_synced_at", "last_event_id", "updated_at"]
        read_only_fields = ["id", "device", "last_synced_at", "updated_at"]


class SyncCursorUpdateSerializer(serializers.Serializer):
    last_synced_at = serializers.DateTimeField(required=False)
    last_event_id = serializers.CharField(max_length=40, required=False, default="")
