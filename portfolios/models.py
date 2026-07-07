import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class PortfolioManager(models.Model):
    """
    ملف مدير المحفظة الاستثمارية المسؤول عن إدارة محافظ عملاء متعددين.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolio_manager_profile"
    )
    license_number = models.CharField(max_length=100, unique=True)
    management_fee_rate = models.DecimalField(
        max_digits=5, decimal_places=3, default=1.0, verbose_name=_("نسبة رسوم الإدارة %")
    )
    years_experience = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "portfolio_managers"
        verbose_name = _("مدير محفظة")
        verbose_name_plural = _("مديرو المحافظ")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - محفظة"


class Portfolio(models.Model):
    """
    محفظة استثمارية تخص متداولًا واحدًا، قد تكون مُدارة ذاتيًا
    أو من قبل مدير محفظة مُعيّن.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolio"
    )
    manager = models.ForeignKey(
        PortfolioManager,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_portfolios",
    )
    cash_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portfolios"
        verbose_name = _("محفظة استثمارية")
        verbose_name_plural = _("المحافظ الاستثمارية")

    def __str__(self):
        return f"محفظة {self.owner.username}"


class Holding(models.Model):
    """
    مركز/حيازة سهم معين داخل محفظة استثمارية.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="holdings")
    stock = models.ForeignKey("market.Stock", on_delete=models.CASCADE, related_name="holdings")
    quantity = models.BigIntegerField(default=0)
    average_buy_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "holdings"
        verbose_name = _("حيازة سهم")
        verbose_name_plural = _("حيازات الأسهم")
        unique_together = ("portfolio", "stock")

    def __str__(self):
        return f"{self.portfolio.owner.username} - {self.stock.symbol} ({self.quantity})"
