from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    # Event CRUD
    path("", views.EventListView.as_view(), name="list"),
    path("calendar/", views.EventCalendarView.as_view(), name="calendar"),
    path("create/", views.EventCreateView.as_view(), name="create"),
    path("<int:pk>/", views.EventDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", views.EventUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.EventDeleteView.as_view(), name="delete"),
    # Event Registration
    path("<int:pk>/register/", views.EventRegisterView.as_view(), name="register"),
    path(
        "<int:pk>/unregister/", views.EventUnregisterView.as_view(), name="unregister"
    ),
    path(
        "<int:pk>/registrations/",
        views.EventRegistrationsView.as_view(),
        name="registrations",
    ),
    # Attendance Management
    path(
        "registration/<int:pk>/update/",
        views.UpdateAttendanceView.as_view(),
        name="update_attendance",
    ),
    # User-specific views
    path("my-events/", views.MyEventsView.as_view(), name="my_events"),
    # API endpoints
    path(
        "api/calendar-data/",
        views.EventCalendarDataView.as_view(),
        name="calendar_data",
    ),
]
