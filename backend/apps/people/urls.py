from django.urls import path

from . import views

urlpatterns = [
    path("people/", views.PersonListCreateView.as_view(), name="person-list"),
    path("people/<uuid:pk>/", views.PersonDetailView.as_view(), name="person-detail"),
    path("people/<uuid:person_id>/employment/", views.EmploymentView.as_view(), name="employment"),
    path("people/<uuid:person_id>/consents/", views.ConsentView.as_view(), name="consent-list"),
    path(
        "people/<uuid:person_id>/consents/grant/",
        views.ConsentGrantView.as_view(),
        name="consent-grant",
    ),
    path(
        "people/<uuid:person_id>/consents/withdraw/",
        views.ConsentWithdrawView.as_view(),
        name="consent-withdraw",
    ),
    path("biometric-templates/", views.BiometricTemplateListView.as_view(), name="template-list"),
]
