from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from datetime import timedelta

from core.mixins import AdminRequiredMixin
from events.models import Event


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

        from accounts.models import CustomUser
        from groups.models import ChurchGroup

        # Basic stats
        context["total_members"] = CustomUser.objects.count()
        context["active_members"] = CustomUser.objects.filter(status="active").count()
        context["visitors"] = CustomUser.objects.filter(status="visitor").count()
        context["total_groups"] = ChurchGroup.objects.count()

        # Recent members
        week_ago = timezone.now() - timedelta(days=7)
        context["recent_members"] = CustomUser.objects.filter(
            date_joined__gte=week_ago
        ).order_by("-date_joined")[:5]

        # Upcoming events
        now = timezone.now()
        context["upcoming_events"] = Event.objects.filter(
            start_datetime__gte=now
        ).order_by("start_datetime")[:5]

        return context


from accounts.models import CustomUser
from groups.models import ChurchGroup, Membership


class GroupLeaderDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/group_leader.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # get groups led by this user
        my_groups = user.leading_groups.all()
        context["my_groups"] = my_groups

        # collect IDs of led groups
        group_ids = my_groups.values_list("id", flat=True)

        # count members using Membership model
        total_members = Membership.objects.filter(group_id__in=group_ids).count()
        context["total_group_members"] = total_members

        return context
