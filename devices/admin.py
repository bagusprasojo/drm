
from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "device_name", "device_hash", "os_version", "app_version", "revoked", "created_at")
    list_filter = ("revoked", "os_version", "app_version")
    search_fields = ("user__email", "device_name", "device_hash")
    readonly_fields = ("created_at",)
