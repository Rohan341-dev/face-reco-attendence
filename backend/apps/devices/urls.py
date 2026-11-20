from django.urls import path

from . import views

urlpatterns = [
    path("devices/auth/", views.DeviceAuthView.as_view(), name="device-auth"),
    path("devices/pair/", views.DevicePairView.as_view(), name="device-pair"),
    path("devices/", views.DeviceListView.as_view(), name="device-list"),
    path("devices/current/", views.CurrentDeviceView.as_view(), name="device-current"),
    path("devices/current/sync-cursor/", views.SyncCursorView.as_view(), name="device-sync-cursor"),
    path("devices/<uuid:pk>/rotate/", views.DeviceRotateView.as_view(), name="device-rotate"),
    path("devices/<uuid:pk>/deactivate/", views.DeviceDeactivateView.as_view(), name="device-deactivate"),
]
