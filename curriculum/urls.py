from django.urls import path
from . import views

# URL Configuration
app_name = "curriculum"

urlpatterns = [
    # Curriculum CRUD
    path("", views.CurriculumListView.as_view(), name="list"),
    path("create/", views.CurriculumCreateView.as_view(), name="create"),
    path("<int:pk>/", views.CurriculumDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", views.CurriculumUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.CurriculumDeleteView.as_view(), name="delete"),
    # Lesson CRUD (all nested under curriculum)
    path(
        "<int:curriculum_id>/lessons/create/",
        views.LessonCreateView.as_view(),
        name="lesson_create",
    ),
    path(
        "<int:curriculum_id>/lessons/<int:pk>/",
        views.LessonDetailView.as_view(),
        name="lesson_detail",
    ),
    path(
        "<int:curriculum_id>/lessons/<int:pk>/update/",
        views.LessonUpdateView.as_view(),
        name="lesson_update",
    ),
    path(
        "<int:curriculum_id>/lessons/<int:pk>/delete/",
        views.LessonDeleteView.as_view(),
        name="lesson_delete",
    ),
    path(
        "<int:curriculum_id>/lessons/<int:pk>/mark-taught/",
        views.LessonMarkTaughtView.as_view(),
        name="lesson_mark_taught",
    ),
    # Attendance (also nested under curriculum/lesson)
    path(
        "<int:curriculum_id>/lessons/<int:lesson_id>/attendance/",
        views.TakeAttendanceView.as_view(),
        name="take_attendance",
    ),
    path(
        "<int:curriculum_id>/lessons/<int:lesson_id>/attendance/bulk/",
        views.BulkAttendanceView.as_view(),
        name="bulk_attendance",
    ),
    path(
        "curriculum/<int:curriculum_id>/lessons/<int:lesson_id>/attendance/<int:pk>/edit/",
        views.AttendanceUpdateView.as_view(),
        name="attendance_edit",
    ),
    path(
        "curriculum/<int:curriculum_id>/lessons/<int:lesson_id>/attendance/<int:pk>/delete/",
        views.AttendanceDeleteView.as_view(),
        name="attendance_delete",
    ),
    # Progress & Enrollment
    path(
        "<int:curriculum_id>/enroll/",
        views.EnrollInCurriculumView.as_view(),
        name="enroll",
    ),
    path(
        "<int:curriculum_id>/lessons/<int:lesson_id>/complete/",
        views.MarkLessonCompleteView.as_view(),
        name="mark_complete",
    ),
    # Dashboard & Statistics
    path("dashboard/", views.CurriculumDashboardView.as_view(), name="dashboard"),
    path("statistics/", views.CurriculumStatisticsView.as_view(), name="statistics"),
]
