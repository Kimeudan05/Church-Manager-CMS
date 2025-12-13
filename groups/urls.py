from django.urls import path
from . import views


app_name = "groups"

urlpatterns = [
    # group CRUD
    path("", views.GroupListView.as_view(), name="list"),
    path("<int:pk>/", views.GroupDetailView.as_view(), name="detail"),
    path("create/", views.GroupCreateView.as_view(), name="create"),
    path("<int:pk>/update/", views.GroupUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.GroupDeleteView.as_view(), name="delete"),
    # Group Memebers
    path("<int:pk>/members/", views.GroupMembersView.as_view(), name="members"),
    path(
        "<int:group_id>/add-member/",
        views.AddGroupMemberView.as_view(),
        name="add_member",
    ),
    path(
        "membership/<int:pk>/update/",
        views.UpdateGroupMemberView.as_view(),
        name="update_member",
    ),
    path(
        "membership/<int:pk>/remove/",
        views.RemoveGroupMemberView.as_view(),
        name="remove_member",
    ),
    # User specific views
    path("my-groups/", views.MyGroupsView.as_view(), name="my_groups"),
    # group leaders
    path(
        "<int:pk>/assign-leaders/",
        views.AssignGroupLeadersView.as_view(),
        name="assign_leaders",
    ),
    # API / JSON endpoints
    path("api/stats/", views.GroupStatsView.as_view(), name="api_stats"),
    path(
        "api/check-member-groups/",
        views.CheckMemberGroupsView.as_view(),
        name="check_member_groups",
    ),
]
