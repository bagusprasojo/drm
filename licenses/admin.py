
from django.contrib import admin

from .models import EbookLicense


@admin.register(EbookLicense)
class EbookLicenseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "ebook", "device", "revoked", "issued_at")
    list_filter = ("revoked", "issued_at")
    search_fields = ("user__email", "ebook__title", "device__device_hash", "device__device_name")
    readonly_fields = ("issued_at",)
