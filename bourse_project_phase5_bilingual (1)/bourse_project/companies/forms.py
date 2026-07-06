from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Company, ListingRequest


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            "legal_name",
            "trade_name",
            "registration_number",
            "sector",
            "founded_year",
            "headquarters",
            "website",
            "logo",
            "description",
        ]
        labels = {
            "legal_name": _("الاسم القانوني للشركة"),
            "trade_name": _("الاسم التجاري"),
            "registration_number": _("رقم السجل التجاري"),
            "sector": _("القطاع الاقتصادي"),
            "founded_year": _("سنة التأسيس"),
            "headquarters": _("المقر الرئيسي"),
            "website": _("الموقع الإلكتروني"),
            "logo": _("شعار الشركة"),
            "description": _("نبذة عن الشركة"),
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class ListingRequestForm(forms.ModelForm):
    class Meta:
        model = ListingRequest
        fields = ["requested_shares", "requested_price_per_share", "requested_symbol"]
        labels = {
            "requested_shares": _("عدد الأسهم المطلوب إدراجها"),
            "requested_price_per_share": _("السعر المقترح للسهم الواحد"),
            "requested_symbol": _("رمز السهم المقترح (اختياري)"),
        }

    def clean_requested_symbol(self):
        symbol = self.cleaned_data.get("requested_symbol", "")
        return symbol.strip().upper()
