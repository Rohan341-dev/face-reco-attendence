"""OpenAPI documentation for the custom device authentication scheme."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class DeviceAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.devices.authentication.DeviceAuthentication"
    name = "deviceTokenAuth"
    match_subclasses = True
    priority = 1

    def get_security_definition(self, auto_schema):  # noqa: ANN001, ANN201
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "Device JWT",
            "description": (
                "Short-lived token from POST /api/devices/auth/ sent as "
                "`Authorization: Device <token>`."
            ),
        }
