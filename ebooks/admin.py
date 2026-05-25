
from django.contrib import admin

from .models import Ebook


@admin.register(Ebook)
class EbookAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "status", "total_pages", "package_format_version", "uploaded_by", "created_at")
    list_filter = ("status", "package_format_version", "created_at")
    search_fields = ("title", "author", "uploaded_by__email")
    readonly_fields = ("created_at",)
