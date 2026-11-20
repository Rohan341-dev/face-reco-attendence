from django.urls import path

from . import views

urlpatterns = [
    path("attendance/events/", views.EventIngestView.as_view(), name="attendance-event-ingest"),
    path("attendance/events/list/", views.EventListView.as_view(), name="attendance-event-list"),
    path("attendance/records/", views.RecordListView.as_view(), name="attendance-records"),
    path("attendance/corrections/", views.CorrectionListCreateView.as_view(), name="attendance-corrections"),
    path("attendance/missing-checkouts/", views.MissingCheckoutListView.as_view(), name="attendance-missing-checkouts"),
    path(
        "attendance/missing-checkouts/<uuid:pk>/resolve/",
        views.MissingCheckoutResolveView.as_view(),
        name="attendance-missing-checkout-resolve",
    ),
    path("attendance/sync/", views.OfflineSyncView.as_view(), name="attendance-offline-sync"),
]
