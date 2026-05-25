from django.conf import settings
from django.db import models


class Device(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    device_hash = models.CharField(max_length=255)
    device_name = models.CharField(max_length=255)
    os_version = models.CharField(max_length=255)
    app_version = models.CharField(max_length=64)
    public_key_pem = models.TextField(blank=True)
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "device_hash"], name="uq_user_device_hash"),
        ]
