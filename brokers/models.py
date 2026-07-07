import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Broker(models.Model):
    """
    ملف السمسار المُرخّص لتنفيذ أوامر التداول نيابة عن العملاء.
    """

    class BrokerStatus(models.TextChoices):
        PENDING = "pending", _("قيد التفعيل")
        ACTIVE = "active", _("نشط")
        SUSPENDED = "suspended", _("موقوف")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="broker_profile"
    )
    license_number = models.CharField(max_length=100, unique=True, verbose_name=_("رقم الترخيص"))
    firm_name = models.CharField(max_length=255, blank=True, verbose_name=_("اسم شركة الوساطة"))
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=3, default=0.5, verbose_name=_("نسبة العمولة %")
    )
    status = models.CharField(max_length=20, choices=BrokerStatus.choices, default=BrokerStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brokers"
        verbose_name = _("سمسار")
        verbose_name_plural = _("السماسرة")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - رخصة {self.license_number}"


class BrokerClient(models.Model):
    """
    ربط بين السمسار والعملاء (متداولين) الذين يوكلونه بتنفيذ أوامرهم.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name="clients")
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="brokers"
    )
    is_active = models.BooleanField(default=True)
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "broker_clients"
        verbose_name = _("عميل سمسار")
        verbose_name_plural = _("عملاء السماسرة")
        unique_together = ("broker", "client")

    def __str__(self):
        return f"{self.client.username} ← {self.broker.user.username}"
