from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("apps.users.auth_urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/admin/", include("apps.users.admin_urls")),
    path("api/admin/", include("apps.datasets.admin_urls")),
    path("api/datasets/", include("apps.datasets.urls")),
    path("api/analysis/", include("apps.analysis.urls")),
    path("api/forecast/", include("apps.forecast.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
