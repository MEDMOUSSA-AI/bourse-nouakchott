from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from .models import Company, FinancialReport, ListingRequest


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("legal_name", "sector", "listing_status", "total_shares_issued", "created_at")
    list_filter = ("listing_status", "sector")
    search_fields = ("legal_name", "registration_number")


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ("company", "report_type", "fiscal_period", "published_at", "is_public")
    list_filter = ("report_type", "is_public")


@admin.register(ListingRequest)
class ListingRequestAdmin(admin.ModelAdmin):
    list_display = ("company", "requested_shares", "requested_price_per_share", "status", "submitted_at")
    list_filter = ("status",)
    actions = ["approve_requests", "reject_requests"]

    @admin.action(description="✅ " + _lazy("الموافقة على الطلبات المحددة وإدراج الأسهم"))
    def approve_requests(self, request, queryset):
        from market.models import Stock  # تفادي الاستيراد الدائري بين التطبيقات

        approved_count = 0
        for listing_request in queryset.exclude(status=ListingRequest.RequestStatus.APPROVED):
            company = listing_request.company

            stock, _created = Stock.objects.get_or_create(
                company=company,
                defaults={
                    "symbol": self._generate_symbol(company, listing_request.requested_symbol),
                    "current_price": listing_request.requested_price_per_share,
                    "previous_close": listing_request.requested_price_per_share,
                    "day_high": listing_request.requested_price_per_share,
                    "day_low": listing_request.requested_price_per_share,
                },
            )

            company.listing_status = Company.ListingStatus.LISTED
            company.total_shares_issued = listing_request.requested_shares
            company.nominal_share_value = listing_request.requested_price_per_share
            company.listed_at = timezone.now()
            company.save()

            listing_request.status = ListingRequest.RequestStatus.APPROVED
            listing_request.decided_at = timezone.now()
            listing_request.save()
            approved_count += 1

        self.message_user(request, _("تمت الموافقة على %(count)s طلب/طلبات وإدراج الأسهم بنجاح.") % {"count": approved_count})

    @admin.action(description="❌ " + _lazy("رفض الطلبات المحددة"))
    def reject_requests(self, request, queryset):
        updated = queryset.exclude(status=ListingRequest.RequestStatus.REJECTED).update(
            status=ListingRequest.RequestStatus.REJECTED, decided_at=timezone.now()
        )
        self.message_user(request, _("تم رفض %(count)s طلب/طلبات.") % {"count": updated})

    @staticmethod
    def _generate_symbol(company, requested_symbol=""):
        from market.models import Stock

        # 1) الأولوية للرمز الذي اقترحته الشركة نفسها عند تقديم طلب الإدراج
        if requested_symbol:
            symbol = requested_symbol
            if not Stock.objects.filter(symbol=symbol).exclude(company=company).exists():
                return symbol

        # 2) محاولة استخراج رمز من الاسم التجاري/القانوني إن كان يحتوي أحرفًا إنجليزية
        source = company.trade_name or company.legal_name
        base = "".join(ch for ch in source if ch.isascii() and ch.isalnum())[:4].upper()
        if not base:
            # اسم الشركة عربي بالكامل ولا يوجد رمز مقترح: نستخدم تسلسلًا رقميًا مميزًا
            # بدل تكرار "CO" لكل الشركات (كان هذا يُنتج نفس الرمز لكل الشركات ذات الأسماء العربية)
            base = "CO"
            suffix = Stock.objects.filter(symbol__startswith=base).count() + 1
            return f"{base}{suffix:03d}"

        symbol = base
        suffix = 1
        while Stock.objects.filter(symbol=symbol).exclude(company=company).exists():
            suffix += 1
            symbol = f"{base}{suffix}"
        return symbol
