from django.urls import path
from . import views

app_name = "sermons"

urlpatterns = [
    # Sermon CRUD
    path("", views.SermonListView.as_view(), name="list"),
    path("create/", views.SermonCreateView.as_view(), name="create"),
    path("<int:pk>/", views.SermonDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", views.SermonUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.SermonDeleteView.as_view(), name="delete"),
    # Archive and Series
    path("archive/", views.SermonArchiveView.as_view(), name="archive"),
    path("archive/<int:year>/", views.SermonArchiveView.as_view(), name="archive_year"),
    path(
        "archive/<int:year>/<int:month>/",
        views.SermonArchiveView.as_view(),
        name="archive_month",
    ),
    path("series/", views.SermonArchiveView.as_view(), name="series_list"),
    path("series/<str:series_name>/", views.SermonSeriesView.as_view(), name="series"),
    # Downloads
    path(
        "<int:pk>/download/<str:file_type>/",
        views.SermonDownloadView.as_view(),
        name="download",
    ),
    # API endpoints
    path("api/statistics/", views.SermonStatisticsView.as_view(), name="statistics"),
]
