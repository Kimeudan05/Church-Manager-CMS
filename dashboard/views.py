from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

from announcements.models import Announcement
from core.mixins import AdminRequiredMixin
from curriculum.models import CurriculumProgress
from events.models import Event


class MemberDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for regular members"""

    template_name = "dashboard/member.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1️⃣ User's groups
        user_groups = ChurchGroup.objects.filter(group_members__member=user)
        context["user_groups"] = user_groups

        # 2️⃣ Upcoming events visible to this member
        now = timezone.now()
        upcoming_events = [
            event
            for event in Event.objects.filter(start_datetime__gte=now)[:20]
            if event.is_visible_to(user)
        ]
        context["upcoming_events"] = upcoming_events[:5]  # show max 5

        # 3️⃣ Relevant announcements
        announcements = (
            Announcement.objects.filter(is_published=True, publish_at__lte=now)
            .filter(
                Q(is_church_wide=True)
                | Q(target_groups__in=user_groups)
                | Q(target_members=user)
            )
            .distinct()
            .order_by("-publish_at")[:5]
        )
        context["recent_announcements"] = announcements

        # 4️⃣ Curriculum progress for this member
        curriculum_progress = CurriculumProgress.objects.filter(member=user)
        context["curriculum_progress"] = curriculum_progress

        # 5️⃣ User info
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

        # Average per group
        group_count = my_groups.count()
        context["average_members_per_group"] = (
            total_members // group_count if group_count > 0 else 0
        )

        return context
