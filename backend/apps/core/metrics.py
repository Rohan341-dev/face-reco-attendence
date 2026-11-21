"""Prometheus instrumentation for the Django API."""

from __future__ import annotations

import hmac
import logging
import re
import time

from django.conf import settings
from django.http import HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = logging.getLogger(__name__)

REQUESTS = Counter(
    "facetrack_http_requests_total",
    "HTTP requests handled by the API",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "facetrack_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
)
UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def route_label(request) -> str:  # noqa: ANN001
    if request.resolver_match and request.resolver_match.url_name:
        return request.resolver_match.url_name
    return UUID_PATTERN.sub(":id", request.path)


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):  # noqa: ANN001, ANN201
        started = time.monotonic()
        response = self.get_response(request)
        label = route_label(request)
        REQUESTS.labels(request.method, label, str(response.status_code)).inc()
        LATENCY.labels(request.method, label).observe(time.monotonic() - started)
        return response


def metrics_view(request):  # noqa: ANN001, ANN201
    """Scrape endpoint guarded by a shared secret (configure in Nginx)."""
    supplied = request.headers.get("X-Metrics-Token", "")
    if not supplied and request.headers.get("Authorization", "").startswith("Bearer "):
        supplied = request.headers["Authorization"].split(None, 1)[1]
    if not hmac.compare_digest(supplied, settings.SECRET_KEY):
        return HttpResponse("Unauthorized", status=401)
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
