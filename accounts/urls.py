from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.dashboard_redirect, name="home"),
    path("login/", views.BourseLoginView.as_view(), name="login"),
    path("logout/", views.BourseLogoutView.as_view(), name="logout"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
    path("documents/", views.document_list, name="documents"),
    # لوحة تحكم إدارة المنصة (مخصصة، بديلة عن /admin/)
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/users/", views.admin_users, name="admin_users"),
    path("admin-dashboard/documents/", views.admin_documents, name="admin_documents"),
    path(
        "admin-dashboard/documents/<uuid:document_id>/review/",
        views.admin_document_review,
        name="admin_document_review",
    ),
    path(
        "admin-dashboard/listing-requests/",
        views.admin_listing_requests,
        name="admin_listing_requests",
    ),
    path(
        "admin-dashboard/listing-requests/<uuid:request_id>/review/",
        views.admin_listing_request_review,
        name="admin_listing_request_review",
    ),
]
