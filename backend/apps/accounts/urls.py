from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.RefreshView.as_view(), name="token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("password/change/", views.ChangePasswordView.as_view(), name="change-password"),
    path("mfa/challenge/", views.MFAVerifyView.as_view(), name="mfa-verify"),
    path("mfa/setup/", views.MFASetupView.as_view(), name="mfa-setup"),
    path("mfa/enable/", views.MFAEnableView.as_view(), name="mfa-enable"),
    path("mfa/disable/", views.MFADisableView.as_view(), name="mfa-disable"),
]
