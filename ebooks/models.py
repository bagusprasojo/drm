from django.conf import settings
from django.db import models


class Ebook(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    source_path = models.CharField(max_length=500)
    package_path = models.CharField(max_length=500, blank=True)
    package_format_version = models.PositiveIntegerField(default=1)
    encrypted_content_key_b64 = models.TextField(blank=True)
    total_pages = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_ebooks")
    created_at = models.DateTimeField(auto_now_add=True)
