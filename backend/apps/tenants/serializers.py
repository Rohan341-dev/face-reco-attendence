from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Branch, Department, Membership, Organization, OrganizationSettings

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "industry", "timezone", "is_active", "created_at"]
        read_only_fields = ["id", "is_active", "created_at"]


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id", "name", "code", "address", "timezone",
            "is_headquarters", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "branch", "parent", "created_at"]
        read_only_fields = ["id", "created_at"]


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "user_email", "user_name", "role", "is_active", "created_at"]
        read_only_fields = ["id", "user", "user_email", "user_name", "created_at"]


class OrganizationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSettings
        fields = "__all__"
        read_only_fields = ["organization"]


class OnboardingSerializer(serializers.Serializer):
    """Creates the first owner account + organization + headquarters branch."""

    organization_name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=60, allow_blank=False)
    industry = serializers.ChoiceField(choices=Organization.Industry.choices, default=Organization.Industry.OTHER)
    timezone = serializers.CharField(max_length=64, default="UTC")
    owner_email = serializers.EmailField()
    owner_username = serializers.CharField(max_length=150)
    owner_first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    owner_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, min_length=10)

    def validate_slug(self, value: str) -> str:
        if Organization.objects.filter(slug=value).exists():
            raise serializers.ValidationError("This slug is already taken.")
        return value

    def validate_owner_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):  # noqa: ANN201, ANN001
        from django.contrib.auth.password_validation import validate_password

        from apps.core.middleware import set_tenant

        validate_password(validated_data["password"])
        org = Organization.objects.create(
            name=validated_data["organization_name"],
            slug=validated_data["slug"],
            industry=validated_data["industry"],
            timezone=validated_data["timezone"],
        )
        # Pin the new tenant so RLS WITH CHECK passes for all child rows.
        set_tenant(str(org.id))
        user = User.objects.create_user(
            email=validated_data["owner_email"],
            username=validated_data["owner_username"],
            first_name=validated_data.get("owner_first_name", ""),
            last_name=validated_data.get("owner_last_name", ""),
            password=validated_data["password"],
        )
        Membership.objects.create(
            user=user, organization=org, role=Membership.Role.OWNER
        )
        Branch.objects.create(
            organization=org, name="Headquarters", is_headquarters=True, timezone=org.timezone
        )
        OrganizationSettings.objects.create(organization=org)
        return {"organization": org, "owner": user}


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=Membership.Role.choices)

    def validate_email(self, value: str) -> str:
        org_id = self.context["organization_id"]
        if Membership.objects.filter(organization_id=org_id, user__email=value).exists():
            raise serializers.ValidationError("This person is already a member.")
        return value

    def create(self, validated_data):  # noqa: ANN201, ANN001
        org_id = self.context["organization_id"]
        email = validated_data["email"]
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": email.split("@")[0][:150]},
        )
        if created:
            # Temporary password flow: user sets password via invite accept endpoint later.
            user.set_unusable_password()
            user.save(update_fields=["password"])
        membership = Membership.objects.create(
            user=user, organization_id=org_id, role=validated_data["role"]
        )
        return {"membership": membership, "user_created": created}
