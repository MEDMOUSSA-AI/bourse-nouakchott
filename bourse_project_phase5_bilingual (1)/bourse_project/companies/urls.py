from django.urls import path

from . import views

app_name = "companies"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile_edit, name="profile_edit"),
    path("listing-request/new/", views.listing_request_create, name="listing_request_create"),
]
