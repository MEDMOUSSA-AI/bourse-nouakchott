from django.urls import path

from . import views

app_name = "portfolios"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile_edit, name="profile_edit"),
    path("adopt/", views.adopt_portfolio, name="adopt_portfolio"),
    path("<uuid:portfolio_id>/", views.portfolio_detail, name="portfolio_detail"),
    path("<uuid:portfolio_id>/release/", views.release_portfolio, name="release_portfolio"),
    path("<uuid:portfolio_id>/order/", views.place_order_for_portfolio, name="place_order_for_portfolio"),
]
