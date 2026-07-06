from django.urls import path

from . import views

app_name = "market"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<uuid:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("stocks/<str:symbol>/", views.stock_detail, name="stock_detail"),
    path("stocks/<str:symbol>/order/", views.place_order, name="place_order"),
]
