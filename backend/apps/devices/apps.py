from django.apps import AppConfig


class DevicesConfig(AppConfig):
    name = "apps.devices"
    verbose_name = "Devices"

    def ready(self):
        from . import schema  # noqa: F401 — registers OpenAPI auth extension
