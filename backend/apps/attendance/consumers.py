"""Authenticated real-time attendance feed (one channel group per tenant)."""

from __future__ import annotations

import logging
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


class AttendanceFeedConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):  # noqa: ANN201
        query = parse_qs(self.scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if not token:
            await self.close(code=4401)
            return
        try:
            validated = JWTAuthentication().get_validated_token(token)
            user = await sync_to_async(JWTAuthentication().get_user)(validated)
            claims = dict(validated.payload)
        except (InvalidToken, TokenError, Exception):  # noqa: BLE001
            await self.close(code=4401)
            return

        org_id = claims.get("org_id")
        requested = self.scope["url_route"]["kwargs"].get("org_id")
        if not org_id or (requested and str(requested) != str(org_id)):
            await self.close(code=4403)
            return
        if not await self._is_member(user.id, org_id):
            await self.close(code=4403)
            return

        self.org_id = str(org_id)
        self.group_name = f"attendance_{self.org_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    @sync_to_async
    def _is_member(self, user_id, org_id):  # noqa: ANN001, ANN201
        from apps.core.middleware import tenant_context
        from apps.tenants.models import Membership

        with tenant_context(None, user_id=user_id):
            return Membership.objects.filter(
                user_id=user_id, organization_id=org_id, is_active=True
            ).exists()

    async def receive_json(self, content, **kwargs):  # noqa: ANN001, ANN003, ANN201
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def attendance_event(self, event):  # noqa: ANN001, ANN201
        await self.send_json(event["event"])

    async def disconnect(self, code):  # noqa: ANN201
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
