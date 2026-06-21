from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from tortobaza.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/", include("accounts.urls")),
    path("api/", include("catalog.urls")),
    path("api/", include("cart.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("attendance.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
