from django.urls import path
from . import views

app_name = "projects"

urlpatterns = [
    # Project CRUD
    path("", views.ProjectListView.as_view(), name="list"),
    path("create/", views.ProjectCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ProjectDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", views.ProjectUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.ProjectDeleteView.as_view(), name="delete"),
    # Task CRUD
    path(
        "<int:project_id>/tasks/create/",
        views.TaskCreateView.as_view(),
        name="task_create",
    ),
    path("tasks/<int:pk>/update/", views.TaskUpdateView.as_view(), name="task_update"),
    path("tasks/<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task_delete"),
    # Dashboard and Views
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("calendar/", views.CalendarView.as_view(), name="calendar"),
    path("gantt/", views.GanttChartView.as_view(), name="gantt"),
    # API endpoints
    path("api/statistics/", views.ProjectStatisticsView.as_view(), name="statistics"),
]
