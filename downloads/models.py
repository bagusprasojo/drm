from django.conf import settings
from django.db import models

from devices.models import Device
from ebooks.models import Ebook


class DownloadLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="download_logs")
    ebook = models.ForeignKey(Ebook, on_delete=models.CASCADE, related_name="download_logs")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="download_logs")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)
