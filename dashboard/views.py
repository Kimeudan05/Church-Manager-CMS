from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from datetime import timedelta

from core.mixins import AdminRequiredMixin


class MemberDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for regular members"""

    template_name = "dashboard/member.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Add user's groups
        context["user_groups"] = user.groups.all() if hasattr(user, "groups") else []
        # Get upcoming events (placeholder - will be implemented in events app)
        # from events.models import Event
        # context['upcoming_events'] = Event.objects.filter(
        #     start_datetime__gte=timezone.now()
        # ).order_by('start_datetime')[:5]

        # placeholder data
        context["upcoming_events"] = []
        context["recent_announcements"] = []
        context["user"] = user

        return context


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Dashboard for admin users"""

    template_name = "dashboard/admin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # import models
        from accounts.models import CustomUser
        from groups.models import ChurchGroup

        # Basic statistics
        context["total_members"] = CustomUser.objects.count()
        context["active_members"] = CustomUser.objects.filter(status="active").count()
        context["visitors"] = CustomUser.objects.filter(status="visitor").count()
        context["total_groups"] = ChurchGroup.objects.count()

        # Recent members (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        context["recent_members"] = CustomUser.objects.filter(
            date_joined__gte=week_ago
        ).order_by("-date_joined")[:5]

        # Placeholder for upcoming events
        # from events.models import Event
        # context['upcoming_events'] = Event.objects.filter(
        #     start_datetime__gte=timezone.now()
        # ).order_by('start_datetime')[:5]
        context["upcoming_events"] = []

        return context


class GroupLeaderDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for group leaders"""

    template_name = "dashboard/group_leader.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        # get group led by this user
        if hasattr(user, "leading_groups"):
            context["my_groups"] = user.leading_groups.all()

            # count members in these groups
            total_members = 0
            for group in context["my_groups"]:
                total_members += group.members.count()

            context["total_group_members"] = total_members
        return context
