from django.contrib import admin

from .models import Order, PriceHistory, Stock, Trade


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("symbol", "company", "current_price", "change_percent", "volume_today", "is_active")
    list_filter = ("is_active",)
    search_fields = ("symbol", "company__legal_name")


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("stock", "date", "open_price", "close_price", "volume")
    list_filter = ("date",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("trader", "stock", "order_type", "quantity", "filled_quantity", "price_per_share", "status")
    list_filter = ("order_type", "status")


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("stock", "quantity", "price_per_share", "executed_at")
