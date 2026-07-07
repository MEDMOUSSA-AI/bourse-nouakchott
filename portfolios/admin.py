from django.contrib import admin

from .models import Holding, Portfolio, PortfolioManager


@admin.register(PortfolioManager)
class PortfolioManagerAdmin(admin.ModelAdmin):
    list_display = ("user", "license_number", "management_fee_rate", "years_experience")


class HoldingInline(admin.TabularInline):
    model = Holding
    extra = 0


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("owner", "manager", "cash_balance", "updated_at")
    inlines = [HoldingInline]


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ("portfolio", "stock", "quantity", "average_buy_price")
