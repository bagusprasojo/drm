
from django.contrib import admin

from .models import DownloadLog


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "ebook", "device", "ip_address", "downloaded_at")
    list_filter = ("downloaded_at",)
    search_fields = ("user__email", "ebook__title", "device__device_hash", "ip_address")
    readonly_fields = ("downloaded_at",)
