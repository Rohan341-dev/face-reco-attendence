from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.metrics import metrics_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/metrics/", metrics_view, name="metrics"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.tenants.urls")),
    path("api/", include("apps.people.urls")),
    path("api/", include("apps.schedules.urls")),
    path("api/", include("apps.attendance.urls")),
    path("api/", include("apps.devices.urls")),
]
