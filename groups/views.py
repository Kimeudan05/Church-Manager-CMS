from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    FormView,
)
from django.db.models import Count, Q
from django.contrib import messages
from django.http import JsonResponse

from core.mixins import AdminRequiredMixin, GroupLeaderRequiredMixin
from .models import ChurchGroup, Membership, UserRole
from .forms import (
    ChurchGroupForm,
    MembershipForm,
    UserRoleForm,
    GroupLeaderAssignmentForm,
)
from accounts.models import CustomUser


class GroupListView(LoginRequiredMixin, ListView):
    """List all church groups"""

    model = ChurchGroup
    template_name = "groups/list.html"
    context_object_name = "groups"
    paginate_by = 12

    def get_queryset(self):
        queryset = ChurchGroup.objects.annotate(
            member_count=Count("group_members")
        ).order_by("name")

        # Filter by group type if specified
        group_type = self.request.GET.get("type")
        if group_type:
            queryset = queryset.filter(group_type=group_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["group_types"] = ChurchGroup.GROUP_TYPES
        return context


class GroupDetailView(LoginRequiredMixin, DetailView):
    """View group details"""

    model = ChurchGroup
    template_name = "groups/detail.html"
    context_object_name = "group"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object

        # Get group members
        context["members"] = (
            Membership.objects.filter(group=group)
            .select_related("member")
            .order_by("-is_primary", "member__last_name")
        )

        # Get group leaders
        context["leaders"] = group.leaders.all()

        # Check if user is a leader of this group
        context["user_is_leader"] = self.request.user in group.leaders.all()

        return context


class GroupCreateView(
    LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, CreateView
):
    """Create a new group (admin only)"""

    model = ChurchGroup
    form_class = ChurchGroupForm
    template_name = "groups/form.html"
    success_url = reverse_lazy("groups:list")
    success_message = "Group created successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create New Group"
        context["submit_text"] = "Create Group"
        return context


class GroupUpdateView(
    LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView
):
    """Update an existing group (admin only)"""

    model = ChurchGroup
    form_class = ChurchGroupForm
    template_name = "groups/form.html"
    success_url = reverse_lazy("groups:list")
    success_message = "Group updated successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Group: {self.object.name}"
        context["submit_text"] = "Update Group"
        return context


class GroupDeleteView(
    LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, DeleteView
):
    """Delete a group (admin only)"""

    model = ChurchGroup
    template_name = "groups/confirm_delete.html"
    success_url = reverse_lazy("groups:list")
    success_message = "Group deleted successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_name"] = self.object.name
        return context


class GroupMembersView(LoginRequiredMixin, DetailView):
    """View and manage group members"""

    model = ChurchGroup
    template_name = "groups/members.html"
    context_object_name = "group"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object

        # Get all members of this group
        memberships = (
            Membership.objects.filter(group=group)
            .select_related("member")
            .order_by("-is_primary", "member__last_name")
        )

        context["memberships"] = memberships

        # Check permissions
        user = self.request.user
        context["can_manage_members"] = (
            user.is_staff
            or hasattr(user, "church_role")
            and (
                user.church_role.role_type in ["super_admin", "church_admin"]
                or user.church_role.can_manage_members
                or user in group.leaders.all()
            )
        )

        # Form for adding new members
        if context["can_manage_members"]:
            context["add_member_form"] = MembershipForm(group=group)

        return context


class AddGroupMemberView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Add a member to a group"""

    model = Membership
    form_class = MembershipForm
    template_name = "groups/add_member.html"

    def get_success_url(self):
        return reverse_lazy("groups:members", kwargs={"pk": self.kwargs["group_id"]})

    def get_success_message(self, cleaned_data):
        return f"Member added to group successfully!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        group_id = self.kwargs.get("group_id")
        group = get_object_or_404(ChurchGroup, pk=group_id)
        kwargs["group"] = group
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group_id = self.kwargs.get("group_id")
        group = get_object_or_404(ChurchGroup, pk=group_id)
        context["group"] = group
        context["title"] = f"Add Member to {group.name}"
        return context

    def form_valid(self, form):
        group_id = self.kwargs.get("group_id")
        group = get_object_or_404(ChurchGroup, pk=group_id)
        form.instance.group = group

        # Check if member already in 3 groups
        member = form.instance.member
        existing_groups = Membership.objects.filter(member=member).count()
        if existing_groups >= 3:
            form.add_error(
                "member",
                f"{member.get_full_name()} already belongs to 3 groups (maximum allowed).",
            )
            return self.form_invalid(form)

        return super().form_valid(form)


class UpdateGroupMemberView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update a member's group membership"""

    model = Membership
    form_class = MembershipForm
    template_name = "groups/update_member.html"

    def get_success_url(self):
        return reverse_lazy("groups:members", kwargs={"pk": self.object.group.id})

    def get_success_message(self, cleaned_data):
        return f"Member information updated successfully!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["group"] = self.object.group
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Update Membership for {self.object.member.get_full_name()}"
        context["group"] = self.object.group
        return context


class RemoveGroupMemberView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Remove a member from a group"""

    model = Membership
    template_name = "groups/confirm_remove_member.html"

    def get_success_url(self):
        return reverse_lazy("groups:members", kwargs={"pk": self.object.group.id})

    def get_success_message(self, cleaned_data):
        return f"Member removed from group successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["group"] = self.object.group
        context["member"] = self.object.member
        return context


class MyGroupsView(LoginRequiredMixin, TemplateView):
    """View groups that the current user belongs to"""

    template_name = "groups/my_groups.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user's group memberships
        memberships = (
            Membership.objects.filter(member=user)
            .select_related("group")
            .order_by("-is_primary", "group__name")
        )

        context["memberships"] = memberships

        # Get groups user leads
        if hasattr(user, "leading_groups"):
            context["leading_groups"] = user.leading_groups.all()

        return context


class AssignGroupLeadersView(LoginRequiredMixin, AdminRequiredMixin, FormView):
    """Assign leaders to a group (admin only)"""

    template_name = "groups/assign_leaders.html"
    form_class = GroupLeaderAssignmentForm

    def get_success_url(self):
        return reverse_lazy("groups:detail", kwargs={"pk": self.kwargs["pk"]})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        group = get_object_or_404(ChurchGroup, pk=self.kwargs["pk"])
        kwargs["group"] = group
        return kwargs

    def form_valid(self, form):
        group = get_object_or_404(ChurchGroup, pk=self.kwargs["pk"])
        leaders = form.cleaned_data["leaders"]
        group.leaders.set(leaders)

        messages.success(self.request, f"Leaders updated for {group.name}")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(ChurchGroup, pk=self.kwargs["pk"])
        context["group"] = group
        context["title"] = f"Assign Leaders to {group.name}"
        return context


# API Views for AJAX calls
class GroupStatsView(LoginRequiredMixin, TemplateView):
    """Get group statistics (JSON)"""

    def get(self, request, *args, **kwargs):
        groups = ChurchGroup.objects.annotate(
            member_count=Count("group_members"), leader_count=Count("leaders")
        ).values("id", "name", "group_type", "member_count", "leader_count")

        return JsonResponse(list(groups), safe=False)


class CheckMemberGroupsView(LoginRequiredMixin, View):
    """Check how many groups a member belongs to (for AJAX)"""

    def get(self, request, *args, **kwargs):
        member_id = request.GET.get("member_id")
        if not member_id:
            return JsonResponse({"error": "Member ID required"}, status=400)

        try:
            member = CustomUser.objects.get(id=member_id)
            group_count = Membership.objects.filter(member=member).count()

            return JsonResponse(
                {
                    "member_name": member.get_full_name(),
                    "group_count": group_count,
                    "can_join_more": group_count < 3,
                }
            )
        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "Member not found"}, status=404)
