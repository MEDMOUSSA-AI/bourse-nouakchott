import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    مستخدم مخصص يحمل دورًا واحدًا من أربعة أدوار رئيسية في المنصة.
    كل دور له لوحة تحكم ونماذج بيانات خاصة به مرتبطة عبر OneToOneField.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", _("مدير المنصة")
        COMPANY = "company", _("شركة مُدرجة")
        BROKER = "broker", _("سمسار")
        PORTFOLIO_MANAGER = "portfolio_manager", _("مدير محفظة استثمارية")
        TRADER = "trader", _("متداول / مستثمر")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TRADER)
    phone_number = models.CharField(max_length=20, blank=True)
    national_id = models.CharField(
        max_length=50, blank=True, help_text=_("رقم الهوية الوطنية / السجل التجاري")
    )
    is_verified = models.BooleanField(
        default=False, help_text=_("تم التحقق من الهوية والمستندات من قبل إدارة المنصة")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        verbose_name = _("مستخدم")
        verbose_name_plural = _("المستخدمون")

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class VerificationDocument(models.Model):
    """
    مستندات إثبات الهوية / السجلات القانونية المرفوعة من المستخدمين
    (شركات، سماسرة، مديري محافظ) للمراجعة قبل تفعيل الحساب.
    """

    class DocStatus(models.TextChoices):
        PENDING = "pending", _("قيد المراجعة")
        APPROVED = "approved", _("مقبول")
        REJECTED = "rejected", _("مرفوض")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=100)
    file = models.FileField(upload_to="verification_docs/%Y/%m/")
    status = models.CharField(
        max_length=20, choices=DocStatus.choices, default=DocStatus.PENDING
    )
    reviewer_note = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "verification_documents"
        verbose_name = _("مستند تحقق")
        verbose_name_plural = _("مستندات التحقق")

    def __str__(self):
        return f"{self.document_type} - {self.user.username} ({self.status})"
