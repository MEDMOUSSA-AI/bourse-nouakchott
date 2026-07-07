from django.contrib import admin

from .models import Broker, BrokerClient


@admin.register(Broker)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ("user", "license_number", "firm_name", "status", "commission_rate")
    list_filter = ("status",)


@admin.register(BrokerClient)
class BrokerClientAdmin(admin.ModelAdmin):
    list_display = ("broker", "client", "is_active", "linked_at")
    list_filter = ("is_active",)
