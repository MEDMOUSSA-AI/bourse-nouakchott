from django.urls import path

from . import views

app_name = "brokers"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile_edit, name="profile_edit"),
    path("clients/add/", views.add_client, name="add_client"),
    path("clients/<uuid:client_link_id>/", views.client_detail, name="client_detail"),
    path("clients/<uuid:client_link_id>/toggle/", views.toggle_client, name="toggle_client"),
    path("clients/<uuid:client_link_id>/order/", views.place_order_for_client, name="place_order_for_client"),
]
