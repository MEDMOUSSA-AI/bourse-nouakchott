from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),  # لتبديل اللغة (عربي/فرنسي)
    path("", include("accounts.urls")),
    path("companies/", include("companies.urls")),
    path("brokers/", include("brokers.urls")),
    path("portfolios/", include("portfolios.urls")),
    path("market/", include("market.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
