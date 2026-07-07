from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.dashboard_redirect, name="home"),
    path("login/", views.BourseLoginView.as_view(), name="login"),
    path("logout/", views.BourseLogoutView.as_view(), name="logout"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("documents/", views.document_list, name="documents"),
]
