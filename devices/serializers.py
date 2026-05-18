from rest_framework import serializers

from .models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["id", "device_hash", "device_name", "os_version", "app_version", "revoked", "created_at"]
        read_only_fields = ["id", "revoked", "created_at"]


class DeviceRevokeSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
