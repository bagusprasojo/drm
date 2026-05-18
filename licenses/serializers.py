from rest_framework import serializers

from .models import EbookLicense


class LicenseVerifySerializer(serializers.Serializer):
    ebook_id = serializers.IntegerField()
    device_id = serializers.IntegerField()


class LicenseIssueSerializer(serializers.Serializer):
    ebook_id = serializers.IntegerField()
    device_id = serializers.IntegerField()


class LicenseRevokeSerializer(serializers.Serializer):
    ebook_id = serializers.IntegerField()
    device_id = serializers.IntegerField()


class EbookLicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EbookLicense
        fields = ["id", "user", "ebook", "device", "issued_at", "revoked"]
        read_only_fields = ["id", "issued_at"]
