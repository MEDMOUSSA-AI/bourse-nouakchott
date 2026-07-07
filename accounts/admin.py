from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, VerificationDocument


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_verified", "is_active", "created_at")
    list_filter = ("role", "is_verified", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        (_("بيانات إضافية"), {"fields": ("role", "phone_number", "national_id", "is_verified")}),
    )


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ("user", "document_type", "status", "uploaded_at")
    list_filter = ("status", "document_type")
