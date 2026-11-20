from django.urls import path

from . import views

urlpatterns = [
    path("organizations/onboarding/", views.OnboardingView.as_view(), name="onboarding"),
    path("organizations/current/", views.CurrentOrganizationView.as_view(), name="current-organization"),
    path("organizations/settings/", views.OrganizationSettingsView.as_view(), name="organization-settings"),
    path("branches/", views.BranchListCreateView.as_view(), name="branch-list"),
    path("branches/<uuid:pk>/", views.BranchDetailView.as_view(), name="branch-detail"),
    path("departments/", views.DepartmentListCreateView.as_view(), name="department-list"),
    path("members/", views.MemberListInviteView.as_view(), name="member-list"),
    path("members/<uuid:pk>/", views.MemberDetailView.as_view(), name="member-detail"),
    path("platform/organizations/", views.PlatformOrganizationListView.as_view(), name="platform-orgs"),
    path(
        "platform/organizations/<uuid:pk>/action/",
        views.PlatformOrganizationActionView.as_view(),
        name="platform-org-action",
    ),
]
