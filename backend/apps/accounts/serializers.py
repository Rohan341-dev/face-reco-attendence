from __future__ import annotations

import pyotp
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import MFADevice, User
from apps.core.crypto import decrypt_text, encrypt_text
from apps.tenants.models import Membership


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "username", "first_name", "last_name",
            "phone", "mfa_enabled", "is_platform_admin", "date_joined",
        ]
        read_only_fields = ["id", "mfa_enabled", "is_platform_admin", "date_joined"]


def _membership_claims(user: User, org_id: str | None) -> tuple[str | None, str | None]:
    # Login/onboarding requests are anonymous, so the middleware has no user
    # GUC set and RLS hides memberships. Pin the user identity for this lookup,
    # then restore the previous value so callers keep their tenant scope.
    from apps.core.middleware import get_guc, set_guc
    from apps.core.rls import USER_GUC

    previous = get_guc(USER_GUC)
    set_guc(USER_GUC, str(user.id))
    try:
        qs = Membership.objects.filter(user=user, is_active=True).select_related("organization")
        if org_id:
            qs = qs.filter(organization_id=org_id)
        membership = qs.order_by("created_at").first()
        if membership is None:
            return None, None
        return str(membership.organization_id), membership.role
    finally:
        set_guc(USER_GUC, previous)


class FaceTrackTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Password login. Returns a short-lived MFA challenge token when the
    account has MFA enabled; otherwise a standard access/refresh pair whose
    claims carry the active organization and role."""

    org_id = serializers.UUIDField(required=False, allow_null=True)

    @classmethod
    def get_token(cls, user):  # noqa: ANN001, ANN201
        token = super().get_token(user)
        org_id, role = _membership_claims(user, None)
        if org_id:
            token["org_id"] = org_id
            token["role"] = role
        token["platform_admin"] = bool(user.is_platform_admin)
        token["mfa_pending"] = False
        return token

    def validate(self, attrs: dict) -> dict:
        request = self.context.get("request")
        data: dict = super().validate(attrs)
        user = self.user

        if user.mfa_enabled:
            challenge = RefreshToken.for_user(user)
            challenge["mfa_pending"] = True
            challenge["org_id"] = attrs.get("org_id") and str(attrs["org_id"]) or None
            if request:
                MFADevice.objects.create(
                    user=user, event="challenge_issued",
                    ip_address=self._client_ip(request),
                )
            data.clear()
            data["mfa_required"] = True
            data["mfa_token"] = str(challenge.access_token)
            return data

        org_id = attrs.get("org_id")
        if org_id:
            resolved, role = _membership_claims(user, str(org_id))
            if resolved is None:
                raise serializers.ValidationError({"org_id": "No active membership for this organization."})
            refresh = RefreshToken.for_user(user)
            refresh["org_id"] = resolved
            refresh["role"] = role
            refresh["platform_admin"] = bool(user.is_platform_admin)
            refresh["mfa_pending"] = False
            access = refresh.access_token
            data = {"refresh": str(refresh), "access": str(access),
                    "org_id": resolved, "role": role}
        else:
            # ensure claims present on default org
            refresh = RefreshToken.for_user(user)
            org, role = _membership_claims(user, None)
            if org:
                refresh["org_id"] = org
                refresh["role"] = role
            refresh["platform_admin"] = bool(user.is_platform_admin)
            refresh["mfa_pending"] = False
            access = refresh.access_token
            data = {"refresh": str(refresh), "access": str(access),
                    "org_id": org, "role": role}
        return data

    @staticmethod
    def _client_ip(request) -> str | None:  # noqa: ANN001
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class MFAVerifySerializer(serializers.Serializer):
    mfa_token = serializers.CharField()
    code = serializers.CharField(max_length=8)

    def validate(self, attrs: dict) -> dict:
        request = self.context.get("request")
        try:
            challenge = AccessToken(attrs["mfa_token"], verify=True)
        except (TokenError, InvalidToken) as exc:
            raise serializers.ValidationError({"mfa_token": "Invalid or expired challenge."}) from exc
        if not challenge.payload.get("mfa_pending"):
            raise serializers.ValidationError({"mfa_token": "Not an MFA challenge token."})
        user = User.objects.get(pk=challenge["user_id"])
        if not user.mfa_enabled:
            raise serializers.ValidationError({"mfa_token": "MFA is not enabled on this account."})
        totp = pyotp.TOTP(decrypt_text(user.mfa_secret_encrypted))
        if not totp.verify(attrs["code"], valid_window=1):
            request = self.context.get("request")
            MFADevice.objects.create(
                user=user, event="challenge_failed",
                ip_address=FaceTrackTokenObtainPairSerializer._client_ip(request) if request else None,
            )
            raise serializers.ValidationError({"code": "Invalid MFA code."})
        org_id = challenge.payload.get("org_id")
        resolved, role = _membership_claims(user, org_id)
        new_refresh = RefreshToken.for_user(user)
        if resolved:
            new_refresh["org_id"] = resolved
            new_refresh["role"] = role
        new_refresh["platform_admin"] = bool(user.is_platform_admin)
        new_refresh["mfa_pending"] = False
        MFADevice.objects.create(
            user=user, event="challenge_passed",
            ip_address=FaceTrackTokenObtainPairSerializer._client_ip(request) if request else None,
        )
        attrs.update({
            "refresh": str(new_refresh),
            "access": str(new_refresh.access_token),
            "org_id": resolved,
            "role": role,
        })
        return attrs


class MFASetupSerializer(serializers.Serializer):
    """Generates (or regenerates) a TOTP secret in pending state."""

    def validate(self, attrs: dict) -> dict:
        user = self.context["request"].user
        if user.mfa_enabled:
            raise serializers.ValidationError("MFA is already enabled; disable it first.")
        secret = pyotp.random_base32()
        user.mfa_secret_encrypted = encrypt_text(secret)
        user.save(update_fields=["mfa_secret_encrypted"])
        attrs.update({
            "secret": secret,
            "otpauth_url": pyotp.totp.TOTP(secret).provisioning_uri(
                name=user.email, issuer_name="FaceTrack AI"
            ),
        })
        return attrs


class MFAEnableSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=8)

    def validate_code(self, value: str) -> str:
        user = self.context["request"].user
        if not user.mfa_secret_encrypted:
            raise serializers.ValidationError("Run MFA setup first.")
        totp = pyotp.TOTP(decrypt_text(user.mfa_secret_encrypted))
        if not totp.verify(value, valid_window=1):
            raise serializers.ValidationError("Invalid code.")
        return value


class AuthTokensSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    org_id = serializers.UUIDField(allow_null=True, required=False)
    role = serializers.CharField(allow_null=True, required=False)


class MFAChallengeSerializer(serializers.Serializer):
    mfa_required = serializers.BooleanField()
    mfa_token = serializers.CharField()


class MFAVerifyResponseSerializer(AuthTokensSerializer):
    pass


class MFASetupResponseSerializer(serializers.Serializer):
    secret = serializers.CharField()
    otpauth_url = serializers.CharField()
    qr_png_base64 = serializers.CharField()


class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value: str) -> str:
        if not authenticate(username=self.context["request"].user.email, password=value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value
