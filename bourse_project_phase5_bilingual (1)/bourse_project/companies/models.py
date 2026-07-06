import uuid
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """
    ملف الشركة المُدرجة أو الراغبة في الإدراج بالبورصة.
    مرتبط بحساب مستخدم بدور 'company'.
    """

    class ListingStatus(models.TextChoices):
        DRAFT = "draft", _("مسودة")
        PENDING_REVIEW = "pending_review", _("قيد المراجعة")
        LISTED = "listed", _("مُدرجة")
        SUSPENDED = "suspended", _("موقوفة")
        DELISTED = "delisted", _("مشطوبة")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_profile"
    )
    legal_name = models.CharField(max_length=255, verbose_name=_("الاسم القانوني للشركة"))
    trade_name = models.CharField(max_length=255, blank=True, verbose_name=_("الاسم التجاري"))
    registration_number = models.CharField(max_length=100, unique=True, verbose_name=_("رقم السجل التجاري"))
    sector = models.CharField(max_length=100, verbose_name=_("القطاع الاقتصادي"))
    founded_year = models.PositiveIntegerField(null=True, blank=True)
    headquarters = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)
    description = models.TextField(blank=True)

    listing_status = models.CharField(
        max_length=20, choices=ListingStatus.choices, default=ListingStatus.DRAFT
    )
    total_shares_issued = models.BigIntegerField(default=0, verbose_name=_("إجمالي الأسهم المُصدرة"))
    nominal_share_value = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name=_("القيمة الاسمية للسهم")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    listed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "companies"
        verbose_name = _("شركة")
        verbose_name_plural = _("الشركات")
        ordering = ["-created_at"]

    def __str__(self):
        return self.legal_name


class FinancialReport(models.Model):
    """
    التقارير المالية الدورية التي تنشرها الشركة (ربع سنوية / سنوية)
    كجزء من متطلبات الإفصاح لدى البورصة.
    """

    class ReportType(models.TextChoices):
        QUARTERLY = "quarterly", _("ربع سنوي")
        ANNUAL = "annual", _("سنوي")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="financial_reports")
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    fiscal_period = models.CharField(max_length=50, verbose_name=_("الفترة المالية"), help_text=_("مثال: Q1 2026"))
    revenue = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    net_profit = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    document = models.FileField(upload_to="financial_reports/%Y/")
    published_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        db_table = "financial_reports"
        verbose_name = _("تقرير مالي")
        verbose_name_plural = _("التقارير المالية")
        ordering = ["-published_at"]

    def __str__(self):
        return f"{self.company.legal_name} - {self.fiscal_period}"


class ListingRequest(models.Model):
    """
    طلب إدراج رسمي تتقدم به الشركة، يخضع لمراجعة إدارة المنصة.
    """

    class RequestStatus(models.TextChoices):
        SUBMITTED = "submitted", _("مُقدَّم")
        UNDER_REVIEW = "under_review", _("قيد الدراسة")
        APPROVED = "approved", _("موافق عليه")
        REJECTED = "rejected", _("مرفوض")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="listing_requests")
    requested_shares = models.BigIntegerField()
    requested_price_per_share = models.DecimalField(max_digits=15, decimal_places=2)
    requested_symbol = models.CharField(
        max_length=6,
        blank=True,
        verbose_name=_("رمز السهم المقترح (Ticker)"),
        help_text=_("حروف إنجليزية و/أو أرقام فقط، من حرفين إلى 6 أحرف (مثال: BZRK). إن تُرك فارغًا سيولّده النظام تلقائيًا."),
        validators=[RegexValidator(r"^[A-Z0-9]{2,6}$", _("استخدم حروفًا إنجليزية كبيرة و/أو أرقامًا فقط (2-6 خانات)."))],
    )
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.SUBMITTED)
    admin_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "listing_requests"
        verbose_name = _("طلب إدراج")
        verbose_name_plural = _("طلبات الإدراج")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"طلب إدراج {self.company.legal_name} ({self.status})"
