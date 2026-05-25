
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("id", "email", "is_staff", "is_superuser", "is_banned", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_banned", "is_active")
    search_fields = ("email", "username")
    ordering = ("email",)
    fieldsets = UserAdmin.fieldsets + (
        ("DRM", {"fields": ("is_banned",)}),
    )
