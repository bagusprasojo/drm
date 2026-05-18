from rest_framework import serializers

from .models import Ebook


class EbookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ebook
        fields = [
            "id",
            "title",
            "author",
            "total_pages",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "total_pages", "status", "created_at"]


class EbookUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    author = serializers.CharField(max_length=255, allow_blank=True, required=False)
    file = serializers.FileField()


class DownloadRequestSerializer(serializers.Serializer):
    ebook_id = serializers.IntegerField()
    device_id = serializers.IntegerField()
