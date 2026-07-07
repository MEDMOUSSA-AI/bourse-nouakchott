from decimal import Decimal

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Order


class OrderForm(forms.ModelForm):
    """
    نموذج تقديم أمر شراء أو بيع لسهم معيّن.
    يدخل الأمر دفتر الأوامر (Order Book) ثم يُمرَّر فورًا على محرك المطابقة
    (market/matching.py) الذي يحاول تنفيذه كليًا أو جزئيًا مقابل الأوامر
    المعاكسة المتوفرة حاليًا، قبل أن يبقى الجزء غير المُنفَّذ (إن وُجد) بحالة "مفتوح".
    """

    class Meta:
        model = Order
        fields = ["order_type", "quantity", "price_per_share"]
        labels = {
            "order_type": _("نوع الأمر"),
            "quantity": _("الكمية (عدد الأسهم)"),
            "price_per_share": _("السعر المحدد للسهم الواحد"),
        }
        widgets = {
            "order_type": forms.Select(attrs={"class": "order-type-select"}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity <= 0:
            raise forms.ValidationError(_("يجب أن تكون الكمية أكبر من صفر."))
        return quantity

    def clean_price_per_share(self):
        price = self.cleaned_data["price_per_share"]
        if price <= Decimal("0"):
            raise forms.ValidationError(_("يجب أن يكون السعر أكبر من صفر."))
        return price
