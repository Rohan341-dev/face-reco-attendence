from django.urls import path

from . import views

urlpatterns = [
    path("shifts/", views.ShiftListCreateView.as_view(), name="shift-list"),
    path("shifts/<uuid:pk>/", views.ShiftDetailView.as_view(), name="shift-detail"),
    path("work-schedules/", views.WorkScheduleListCreateView.as_view(), name="schedule-list"),
    path("work-schedules/<uuid:pk>/", views.WorkScheduleDetailView.as_view(), name="schedule-detail"),
    path("holidays/", views.HolidayListCreateView.as_view(), name="holiday-list"),
    path("holidays/<uuid:pk>/", views.HolidayDetailView.as_view(), name="holiday-detail"),
    path("leave-requests/", views.LeaveRequestListCreateView.as_view(), name="leave-list"),
    path(
        "leave-requests/<uuid:pk>/decision/",
        views.LeaveRequestDecisionView.as_view(),
        name="leave-decision",
    ),
]
