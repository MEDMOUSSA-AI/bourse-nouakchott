from decimal import Decimal

from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from market.models import Order, Stock

from .models import Broker


class BrokerProfileForm(forms.ModelForm):
    class Meta:
        model = Broker
        fields = ["license_number", "firm_name", "commission_rate"]
        labels = {
            "license_number": _("رقم الترخيص"),
            "firm_name": _("اسم شركة الوساطة"),
            "commission_rate": _("نسبة العمولة %"),
        }


class AddClientForm(forms.Form):
    """
    ربط متداول موجود كعميل للسمسار عبر اسم المستخدم، بدلاً من طلب
    تسجيل جديد — العميل يملك حسابه الخاص أصلاً بدور "متداول".
    """

    client_username = forms.CharField(label=_("اسم مستخدم العميل (المتداول)"), max_length=150)

    def __init__(self, *args, broker=None, **kwargs):
        self.broker = broker
        super().__init__(*args, **kwargs)

    def clean_client_username(self):
        username = self.cleaned_data["client_username"].strip()
        try:
            user = User.objects.get(username=username, role=User.Role.TRADER)
        except User.DoesNotExist:
            raise forms.ValidationError(_("لا يوجد متداول بهذا اسم المستخدم."))

        if self.broker and self.broker.clients.filter(client=user).exists():
            raise forms.ValidationError(_("هذا المتداول مرتبط بك بالفعل كعميل."))

        self.cleaned_data["client_user"] = user
        return username


class BrokerOrderForm(forms.Form):
    """
    نموذج تنفيذ أمر شراء/بيع نيابة عن عميل مرتبط بالسمسار، من أي سهم مُدرج
    (على خلاف نموذج المتداول الذي يُقدَّم من صفحة سهم محددة سلفًا).
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
