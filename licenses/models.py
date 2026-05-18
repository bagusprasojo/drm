from django.conf import settings
from django.db import models

from devices.models import Device
from ebooks.models import Ebook


class EbookLicense(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ebook_licenses")
    ebook = models.ForeignKey(Ebook, on_delete=models.CASCADE, related_name="licenses")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="licenses")
    issued_at = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "ebook"], name="uq_user_ebook_license"),
        ]
