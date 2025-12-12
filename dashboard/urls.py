from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.MemberDashboardView.as_view(), name="member"),
    path("admin/", views.AdminDashboardView.as_view(), name="admin"),
    path(
        "group_leader/", views.GroupLeaderDashboardView.as_view(), name="group_leader"
    ),
]
