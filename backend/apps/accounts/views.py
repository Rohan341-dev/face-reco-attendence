from __future__ import annotations

import qrcode
import pyotp
from django.contrib.auth import logout as django_logout
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.crypto import decrypt_text
from apps.core.exceptions import error_response
from .models import MFADevice, User
from .serializers import (
    ChangePasswordSerializer,
    FaceTrackTokenObtainPairSerializer,
    MFAEnableSerializer,
    MFASetupSerializer,
    MFAVerifySerializer,
    UserSerializer,
)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "anon"

    @extend_schema(request=FaceTrackTokenObtainPairSerializer)
    def post(self, request):  # noqa: ANN001, ANN201
        serializer = FaceTrackTokenObtainPairSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):  # noqa: ANN001, ANN201
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer

        try:
            serializer = TokenRefreshSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError) as exc:
            return error_response("Invalid refresh token.", 401, "invalid_token")
        data = serializer.validated_data
        # propagate org claims from the refreshed access token
        try:
            from rest_framework_simplejwt.tokens import AccessToken

            token = AccessToken(data["access"])
            data["org_id"] = token.payload.get("org_id")
            data["role"] = token.payload.get("role")
            data["platform_admin"] = token.payload.get("platform_admin", False)
        except Exception:  # noqa: BLE001
            pass
        return Response(data)


class MFAVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):  # noqa: ANN001, ANN201
        serializer = MFAVerifySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class MFASetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001, ANN201
        serializer = MFASetupSerializer(data={}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        secret = serializer.validated_data["secret"]
        qr = qrcode.make(serializer.validated_data["otpauth_url"])
        import base64
        import io

        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        data = {
            "secret": secret,
            "otpauth_url": serializer.validated_data["otpauth_url"],
            "qr_png_base64": base64.b64encode(buf.getvalue()).decode(),
        }
        return Response(data)


class MFAEnableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001, ANN201
        serializer = MFAEnableSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.mfa_enabled = True
        user.save(update_fields=["mfa_enabled", "updated_at"])
        MFADevice.objects.create(
            user=user, event="enabled",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response({"mfa_enabled": True})


class MFADisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001, ANN201
        code = str(request.data.get("code", ""))
        user = request.user
        if not user.mfa_enabled:
            return error_response("MFA is not enabled.", 400, "mfa_not_enabled")
        totp = pyotp.TOTP(decrypt_text(user.mfa_secret_encrypted))
        if not totp.verify(code, valid_window=1):
            return error_response("Invalid MFA code.", 400, "invalid_code")
        user.mfa_enabled = False
        user.mfa_secret_encrypted = ""
        user.save(update_fields=["mfa_enabled", "mfa_secret_encrypted", "updated_at"])
        MFADevice.objects.create(user=user, event="disabled", ip_address=request.META.get("REMOTE_ADDR"))
        return Response({"mfa_enabled": False})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema responses=UserSerializer)
    def get(self, request):  # noqa: ANN001, ANN201
        memberships = request.user.memberships.select_related("organization").filter(is_active=True)
        data = UserSerializer(request.user).data
        data["memberships"] = [
            {
                "organization_id": str(m.organization_id),
                "organization_name": m.organization.name,
                "role": m.role,
            }
            for m in memberships
        ]
        data["active_organization_id"] = getattr(request, "organization_id", None)
        return Response(data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001, ANN201
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        # invalidate other sessions
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        return Response({"detail": "Password changed."})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001, ANN201
        try:
            refresh = request.data.get("refresh")
            if refresh:
                token = RefreshToken(refresh)
                token.blacklist()
        except Exception:  # noqa: BLE001
            pass
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
