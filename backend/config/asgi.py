import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

django_asgi_app = get_asgi_application()

from apps.attendance.consumers import AttendanceFeedConsumer  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter(
            [
                path("ws/attendance/", AttendanceFeedConsumer.as_asgi()),
                path("ws/attendance/<uuid:org_id>/", AttendanceFeedConsumer.as_asgi()),
            ]
        ),
    }
)
