from decimal import Decimal

from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from market.models import Order, Stock

from .models import Portfolio, PortfolioManager


class PortfolioManagerProfileForm(forms.ModelForm):
    class Meta:
        model = PortfolioManager
        fields = ["license_number", "management_fee_rate", "years_experience"]
        labels = {
            "license_number": _("رقم الترخيص"),
            "management_fee_rate": _("نسبة رسوم الإدارة %"),
            "years_experience": _("سنوات الخبرة"),
        }


class AdoptPortfolioForm(forms.Form):
    """
    إسناد محفظة متداول موجود إلى مدير المحفظة عبر اسم المستخدم، بشرط ألا
    تكون تلك المحفظة مُدارة من طرف مدير آخر مسبقًا.
    """

    owner_username = forms.CharField(label=_("اسم مستخدم صاحب المحفظة (المتداول)"), max_length=150)

    def clean_owner_username(self):
        username = self.cleaned_data["owner_username"].strip()
        try:
            owner = User.objects.get(username=username, role=User.Role.TRADER)
        except User.DoesNotExist:
            raise forms.ValidationError(_("لا يوجد متداول بهذا اسم المستخدم."))

        portfolio, _created = Portfolio.objects.get_or_create(owner=owner)
        if portfolio.manager_id:
            raise forms.ValidationError(
                _("محفظة %(username)s مُدارة بالفعل من طرف مدير محفظة آخر.") % {"username": owner.username}
            )

        self.cleaned_data["portfolio"] = portfolio
        return username


class ManagerOrderForm(forms.Form):
    """
    نموذج تنفيذ أمر شراء/بيع نيابة عن صاحب محفظة يديرها مدير المحفظة.
    """

    stock = forms.ModelChoiceField(
        queryset=Stock.objects.filter(is_active=True),
        label=_("السهم"),
        empty_label=_("اختر سهمًا مُدرجًا"),
    )
    order_type = forms.ChoiceField(choices=Order.OrderType.choices, label=_("نوع الأمر"))
    quantity = forms.IntegerField(min_value=1, label=_("الكمية (عدد الأسهم)"))
    price_per_share = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label=_("السعر المحدد للسهم الواحد"),
    )
