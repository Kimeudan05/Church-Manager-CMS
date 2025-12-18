from django.contrib.auth.mixins import (
    AccessMixin,
    UserPassesTestMixin,
    LoginRequiredMixin,
)
from django.shortcuts import get_object_or_404
from curriculum.models import Curriculum, Lesson
from django.db.models import Q


class GroupLeaderRequiredMixin(AccessMixin):
    """Verify that the current user is a group leader"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not hasattr(request.user, "church_role"):
            return self.handle_no_permission()
        if request.user.church_role.role_type != "group_leader":
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(AccessMixin):
    """Verify that the current user is a admin user"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not hasattr(request.user, "church_role"):
            return self.handle_no_permission()
        if request.user.church_role.role_type not in ["super_admin", "church_admin"]:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


# Curriculum Mixins


# Mixins for permission handling
class CurriculumAccessMixin(LoginRequiredMixin):
    """Access control for Curriculum views ONLY"""

    def get_queryset(self):
        user = self.request.user

        if user.church_role.role_type in ["super_admin", "church_admin", "sub_admin"]:
            return Curriculum.objects.all()

        groups_led = user.leading_groups.all()
        return Curriculum.objects.filter(
            Q(created_by=user)
            | Q(target_group__in=groups_led)
            | Q(target_group__group_members__member=user)
        ).distinct()


class CanManageCurriculumMixin(UserPassesTestMixin):
    """Check if user can manage curriculum"""

    def test_func(self):
        user = self.request.user

        if user.church_role.role_type in ["super_admin", "church_admin", "sub_admin"]:
            return True

        # Group leaders can manage curriculums for their groups
        if self.kwargs.get("pk"):
            curriculum = get_object_or_404(Curriculum, pk=self.kwargs["pk"])
            return curriculum.target_group in user.leading_groups.all()

        return (
            user.church_role.can_manage_members
            or user.church_role.role_type == "teacher"
        )


# core/mixins.py
class LessonAccessMixin(LoginRequiredMixin):
    """Access control for Lesson views"""

    def get_queryset(self):
        user = self.request.user

        qs = Lesson.objects.select_related("curriculum", "curriculum__target_group")

        if user.church_role.role_type in ["super_admin", "church_admin", "sub_admin"]:
            return qs

        groups_led = user.leading_groups.all()
        return qs.filter(
            Q(curriculum__created_by=user)
            | Q(curriculum__target_group__in=groups_led)
            | Q(curriculum__target_group__group_members__member=user)
        ).distinct()
