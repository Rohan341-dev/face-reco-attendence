"""APIView base that exposes a serializer to drf-spectacular so response
schemas appear in the generated OpenAPI contract."""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.views import APIView


class ContractAPIView(APIView):
    serializer_class: type[serializers.Serializer] | None = None

    def get_serializer_class(self):  # noqa: ANN201
        return self.serializer_class

    def get_serializer(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        if self.serializer_class is None:
            return None
        return self.serializer_class(*args, **kwargs)
