import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class TenantMismatchError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have access to this organization."
    default_code = "tenant_mismatch"


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    response.data = {
        "error": {
            "status": response.status_code,
            "code": getattr(exc, "code", None) or getattr(exc, "default_code", "error"),
            "detail": response.data if not isinstance(response.data, dict) else response.data,
        }
    }
    return response


def error_response(message: str, status_code: int = 400, code: str = "error") -> Response:
    return Response({"error": {"status": status_code, "code": code, "detail": message}}, status=status_code)
