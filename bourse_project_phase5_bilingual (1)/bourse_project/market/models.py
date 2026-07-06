import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Stock(models.Model):
    """
    سهم مُدرج في السوق، مرتبط بشركة واحدة.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.OneToOneField(
        "companies.Company", on_delete=models.CASCADE, related_name="stock"
    )
    symbol = models.CharField(max_length=10, unique=True, verbose_name=_("الرمز"))
    current_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    previous_close = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    day_high = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    day_low = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    volume_today = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stocks"
        verbose_name = _("سهم")
        verbose_name_plural = _("الأسهم")

    def __str__(self):
        return f"{self.symbol} - {self.company.legal_name}"

    @property
    def change_percent(self):
        if self.previous_close == 0:
            return 0
        return round(
            (float(self.current_price) - float(self.previous_close))
            / float(self.previous_close)
            * 100,
            2,
        )


class PriceHistory(models.Model):
    """
    سجل تاريخي لأسعار الإغلاق اليومية لكل سهم، يُستخدم للرسوم البيانية.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="price_history")
    date = models.DateField()
    open_price = models.DecimalField(max_digits=15, decimal_places=2)
    close_price = models.DecimalField(max_digits=15, decimal_places=2)
    high_price = models.DecimalField(max_digits=15, decimal_places=2)
    low_price = models.DecimalField(max_digits=15, decimal_places=2)
    volume = models.BigIntegerField(default=0)

    class Meta:
        db_table = "price_history"
        verbose_name = _("سجل سعري")
        verbose_name_plural = _("السجلات السعرية")
        unique_together = ("stock", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.stock.symbol} - {self.date}"


class Order(models.Model):
    """
    أمر شراء أو بيع مُقدَّم من متداول (مباشرة أو عبر سمسار)،
    يبقى في دفتر الأوامر حتى يُنفَّذ أو يُلغى.
    """

    class OrderType(models.TextChoices):
        BUY = "buy", _("شراء")
        SELL = "sell", _("بيع")

    class OrderStatus(models.TextChoices):
        OPEN = "open", _("مفتوح")
        PARTIALLY_FILLED = "partially_filled", _("منفَّذ جزئيًا")
        FILLED = "filled", _("منفَّذ بالكامل")
        CANCELLED = "cancelled", _("مُلغى")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trader = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="orders"
    )
    broker = models.ForeignKey(
        "brokers.Broker", on_delete=models.SET_NULL, null=True, blank=True, related_name="executed_orders"
    )
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="orders")
    order_type = models.CharField(max_length=10, choices=OrderType.choices)
    quantity = models.BigIntegerField()
    filled_quantity = models.BigIntegerField(default=0)
    price_per_share = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        verbose_name = _("أمر تداول")
        verbose_name_plural = _("أوامر التداول")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_order_type_display()} {self.quantity} {self.stock.symbol} @ {self.price_per_share}"


class Trade(models.Model):
    """
    صفقة مُنفَّذة فعليًا، ناتجة عن مطابقة أمر شراء مع أمر بيع.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="trades")
    buy_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="buy_trades")
    sell_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="sell_trades")
    quantity = models.BigIntegerField()
    price_per_share = models.DecimalField(max_digits=15, decimal_places=2)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trades"
        verbose_name = _("صفقة")
        verbose_name_plural = _("الصفقات")
        ordering = ["-executed_at"]

    def __str__(self):
        return f"{self.stock.symbol} x{self.quantity} @ {self.price_per_share}"
