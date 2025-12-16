from django.urls import path
from . import views

app_name = "announcements"

urlpatterns = [
    # Main views
    path("", views.AnnouncementListView.as_view(), name="list"),
    path("create/", views.AnnouncementCreateView.as_view(), name="create"),
    path("<int:pk>/", views.AnnouncementDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", views.AnnouncementUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.AnnouncementDeleteView.as_view(), name="delete"),
    # Quick create (for modals/AJAX)
    path(
        "quick-create/",
        views.AnnouncementQuickCreateView.as_view(),
        name="quick_create",
    ),
    # User-specific views
    path(
        "my-announcements/",
        views.MyAnnouncementsView.as_view(),
        name="my_announcements",
    ),
    path("dashboard/", views.AnnouncementDashboardView.as_view(), name="dashboard"),
    # API endpoints
    path(
        "api/statistics/", views.AnnouncementStatisticsView.as_view(), name="statistics"
    ),
]
