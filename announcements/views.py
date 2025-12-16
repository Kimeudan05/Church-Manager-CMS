from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    FormView,
)
from django.db.models import Q, Count
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from collections import Counter

from .models import Announcement
from .forms import AnnouncementForm, AnnouncementFilterForm, AnnouncementQuickCreateForm
from groups.models import ChurchGroup, Membership
from accounts.models import CustomUser


class AnnouncementListView(LoginRequiredMixin, ListView):
    """List announcements for the current user"""

    model = Announcement
    template_name = "announcements/list.html"
    context_object_name = "announcements"
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()

        # Base queryset with prefetching
        queryset = (
            Announcement.objects.filter(is_published=True, publish_at__lte=now)
            .select_related("author")
            .prefetch_related("target_groups", "target_members")
            .order_by("-priority", "-publish_at")
        )

        # Get user's groups
        user_groups = []
        if hasattr(user, "memberships"):
            user_groups = user.memberships.values_list("group", flat=True)

        # Filter announcements visible to this user
        visible_announcements = []
        for announcement in queryset:
            if announcement.is_church_wide:
                visible_announcements.append(announcement.id)
            elif announcement.target_groups.filter(id__in=user_groups).exists():
                visible_announcements.append(announcement.id)
            elif announcement.target_members.filter(id=user.id).exists():
                visible_announcements.append(announcement.id)
            # Also show announcements where user is the author
            elif announcement.author == user:
                visible_announcements.append(announcement.id)

        # Apply final filter
        queryset = Announcement.objects.filter(id__in=visible_announcements)

        # Apply additional filters from form
        form = AnnouncementFilterForm(self.request.GET)
        if form.is_valid():
            priority = form.cleaned_data.get("priority")
            status = form.cleaned_data.get("status")
            is_church_wide = form.cleaned_data.get("is_church_wide")
            start_date = form.cleaned_data.get("start_date")
            end_date = form.cleaned_data.get("end_date")
            search = form.cleaned_data.get("search")
            author = form.cleaned_data.get("author")

            if priority:
                queryset = queryset.filter(priority=priority)

            if status:
                if status == "published":
                    queryset = queryset.filter(is_published=True, publish_at__lte=now)
                elif status == "scheduled":
                    queryset = queryset.filter(is_published=True, publish_at__gt=now)
                elif status == "expired":
                    queryset = queryset.filter(expires_at__lt=now)
                elif status == "draft":
                    queryset = queryset.filter(is_published=False)

            if is_church_wide == "yes":
                queryset = queryset.filter(is_church_wide=True)
            elif is_church_wide == "no":
                queryset = queryset.filter(is_church_wide=False)

            if start_date:
                queryset = queryset.filter(publish_at__date__gte=start_date)

            if end_date:
                queryset = queryset.filter(publish_at__date__lte=end_date)

            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search)
                    | Q(content__icontains=search)
                    | Q(author__first_name__icontains=search)
                    | Q(author__last_name__icontains=search)
                )

            if author:
                queryset = queryset.filter(author=author)

        return queryset.order_by("-publish_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()

        # Announcement statistics for the current user
        total_announcements = self.get_queryset().count()

        # Get urgent announcements
        urgent_announcements = (
            self.get_queryset().filter(priority="urgent", expires_at__gt=now).count()
        )

        # Get announcements from last 7 days
        week_ago = now - timezone.timedelta(days=7)
        recent_announcements = (
            self.get_queryset().filter(publish_at__gte=week_ago).count()
        )

        # Get user's groups for filtering
        user_groups = []
        if hasattr(user, "memberships"):
            user_groups = Membership.objects.filter(member=user).select_related("group")

        # Prepare announcements by priority for dashboard
        announcements_by_priority = {}
        for priority_code, priority_name in Announcement.PRIORITY_LEVELS:
            count = (
                self.get_queryset()
                .filter(priority=priority_code, expires_at__gt=now)
                .count()
            )
            announcements_by_priority[priority_name] = count

        context.update(
            {
                "filter_form": AnnouncementFilterForm(self.request.GET),
                "total_announcements": total_announcements,
                "urgent_announcements": urgent_announcements,
                "recent_announcements": recent_announcements,
                "user_groups": user_groups,
                "announcements_by_priority": announcements_by_priority,
                "today": now.date(),
                "can_create_announcement": self.can_create_announcement(user),
            }
        )

        return context

    def can_create_announcement(self, user):
        """Check if user can create announcements"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return True

            if user.church_role.can_send_announcements:
                return True

        return False


class AnnouncementDetailView(LoginRequiredMixin, DetailView):
    """View announcement details"""

    model = Announcement
    template_name = "announcements/detail.html"
    context_object_name = "announcement"

    def dispatch(self, request, *args, **kwargs):
        # Get the announcement
        self.object = self.get_object()
        user = request.user

        # Check if user can view this announcement
        if not self.can_view_announcement(user, self.object):
            messages.error(
                request, "You don't have permission to view this announcement."
            )
            return redirect("announcements:list")

        return super().dispatch(request, *args, **kwargs)

    def can_view_announcement(self, user, announcement):
        """Check if user can view this specific announcement"""
        if not user.is_authenticated:
            return False

        # Author can always view their own announcements
        if announcement.author == user:
            return True

        # Check if announcement is published and not expired
        now = timezone.now()
        if not announcement.is_published or announcement.publish_at > now:
            return False

        # Check if announcement is church-wide
        if announcement.is_church_wide:
            return True

        # Check if user is in target groups
        user_groups = []
        if hasattr(user, "memberships"):
            user_groups = user.memberships.values_list("group", flat=True)

        if announcement.target_groups.filter(id__in=user_groups).exists():
            return True

        # Check if user is in target members
        if announcement.target_members.filter(id=user.id).exists():
            return True

        # Admins can view all announcements
        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return True

        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        announcement = self.object
        user = self.request.user
        now = timezone.now()

        # Check if announcement is expired
        is_expired = announcement.expires_at and announcement.expires_at < now

        # Check if user can edit/delete
        can_edit = self.can_edit_announcement(user, announcement)
        can_delete = self.can_delete_announcement(user, announcement)

        # Get target information
        target_info = self.get_target_info(announcement)

        # Get related announcements (same author or same priority)
        related_announcements = (
            Announcement.objects.filter(
                Q(author=announcement.author) | Q(priority=announcement.priority),
                is_published=True,
                publish_at__lte=now,
            )
            .exclude(id=announcement.id)
            .order_by("-publish_at")[:5]
        )

        context.update(
            {
                "is_expired": is_expired,
                "can_edit": can_edit,
                "can_delete": can_delete,
                "target_info": target_info,
                "related_announcements": related_announcements,
                "now": now,
            }
        )

        return context

    def can_edit_announcement(self, user, announcement):
        """Check if user can edit this announcement"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if announcement.author == user:
            # Authors can edit their own announcements within 1 hour of creation
            time_since_creation = timezone.now() - announcement.created_at
            if time_since_creation.total_seconds() <= 3600:  # 1 hour
                return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return True

        return False

    def can_delete_announcement(self, user, announcement):
        """Check if user can delete this announcement"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return True

        return False

    def get_target_info(self, announcement):
        """Get information about who can see this announcement"""
        if announcement.is_church_wide:
            return {
                "type": "church_wide",
                "description": "Visible to all church members",
                "icon": "fas fa-church",
                "color": "primary",
            }

        target_groups = announcement.target_groups.all()
        target_members = announcement.target_members.all()

        if target_groups.exists() and target_members.exists():
            return {
                "type": "mixed",
                "description": f"Visible to {target_groups.count()} group(s) and {target_members.count()} member(s)",
                "icon": "fas fa-users",
                "color": "info",
            }
        elif target_groups.exists():
            group_names = ", ".join([g.name for g in target_groups[:3]])
            if target_groups.count() > 3:
                group_names += f" and {target_groups.count() - 3} more"
            return {
                "type": "groups",
                "description": f"Visible to: {group_names}",
                "icon": "fas fa-user-friends",
                "color": "success",
            }
        else:
            member_names = ", ".join(
                [m.get_full_name() or m.username for m in target_members[:3]]
            )
            if target_members.count() > 3:
                member_names += f" and {target_members.count() - 3} more"
            return {
                "type": "members",
                "description": f"Visible to: {member_names}",
                "icon": "fas fa-user",
                "color": "warning",
            }


class AnnouncementCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new announcement"""

    model = Announcement
    form_class = AnnouncementForm
    template_name = "announcements/form.html"
    success_message = "Announcement created successfully!"

    def get_success_url(self):
        return reverse_lazy("announcements:detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create New Announcement"
        context["submit_text"] = "Create Announcement"
        context["is_quick_form"] = False
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to create announcements
        if not self.can_create_announcement(request.user):
            messages.error(
                request, "You don't have permission to create announcements."
            )
            return redirect("announcements:list")

        return super().dispatch(request, *args, **kwargs)

    def can_create_announcement(self, user):
        """Check if user can create announcements"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return True

            if user.church_role.can_send_announcements:
                return True

        return False

    def form_valid(self, form):
        # Set author to current user
        form.instance.author = self.request.user

        response = super().form_valid(form)

        # Show different message based on publish status
        if form.instance.is_published:
            if form.instance.publish_at <= timezone.now():
                messages.success(self.request, "Announcement published successfully!")
            else:
                messages.success(self.request, "Announcement scheduled successfully!")
        else:
            messages.success(self.request, "Announcement saved as draft.")

        return response


class AnnouncementUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update an existing announcement"""

    model = Announcement
    form_class = AnnouncementForm
    template_name = "announcements/form.html"
    success_message = "Announcement updated successfully!"

    def get_success_url(self):
        return reverse_lazy("announcements:detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Announcement: {self.object.title}"
        context["submit_text"] = "Update Announcement"
        context["is_quick_form"] = False
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to edit this announcement
        self.object = self.get_object()

        if not self.can_edit_announcement(request.user, self.object):
            messages.error(
                request, "You don't have permission to edit this announcement."
            )
            return redirect("announcements:detail", pk=self.object.pk)

        return super().dispatch(request, *args, **kwargs)

    def can_edit_announcement(self, user, announcement):
        """Check if user can edit this announcement"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if announcement.author == user:
            # Authors can edit their own announcements within 1 hour of creation
            time_since_creation = timezone.now() - announcement.created_at
            if time_since_creation.total_seconds() <= 3600:  # 1 hour
                return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return True

        return False


class AnnouncementDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete an announcement"""

    model = Announcement
    template_name = "announcements/confirm_delete.html"
    success_url = reverse_lazy("announcements:list")
    success_message = "Announcement deleted successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target_count"] = (
            self.object.target_groups.count() + self.object.target_members.count()
        )
        # Announcements by priority
        priority_stats = []
        now = timezone.now()
        for priority_code, priority_name in Announcement.PRIORITY_LEVELS:
            count = Announcement.objects.filter(
                priority=priority_code,
                is_published=True,
                publish_at__lte=now,
                expires_at__gt=now,
            ).count()
            priority_stats.append(
                {
                    "name": priority_name,
                    "code": priority_code,
                    "count": count,
                    "color": self.get_priority_color(priority_code),
                }
            )
        context["priority_stats"] = priority_stats
        return context

    def get_priority_color(self, priority_code):
        """Get Bootstrap color for priority level"""
        colors = {
            "urgent": "danger",
            "high": "warning",
            "normal": "primary",
            "low": "secondary",
        }
        return colors.get(priority_code, "secondary")

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to delete announcements
        self.object = self.get_object()

        if not self.can_delete_announcement(request.user, self.object):
            messages.error(
                request, "You don't have permission to delete this announcement."
            )
            return redirect("announcements:detail", pk=self.object.pk)

        return super().dispatch(request, *args, **kwargs)

    def can_delete_announcement(self, user, announcement):
        """Check if user can delete this announcement"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return True

        return False


class AnnouncementQuickCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Quick create announcement (modal/form)"""

    model = Announcement
    form_class = AnnouncementQuickCreateForm
    template_name = "announcements/quick_form.html"
    success_message = "Quick announcement created successfully!"

    def get_success_url(self):
        return reverse_lazy("announcements:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to create announcements
        if not self.can_create_announcement(request.user):
            return HttpResponseForbidden(
                "You don't have permission to create announcements."
            )

        return super().dispatch(request, *args, **kwargs)

    def can_create_announcement(self, user):
        """Check if user can create announcements"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return True

            if user.church_role.can_send_announcements:
                return True

        return False

    def form_valid(self, form):
        response = super().form_valid(form)

        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "message": self.success_message,
                    "announcement_id": self.object.id,
                }
            )

        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors})

        return super().form_invalid(form)


class MyAnnouncementsView(LoginRequiredMixin, ListView):
    """View announcements created by the current user"""

    model = Announcement
    template_name = "announcements/my_announcements.html"
    context_object_name = "announcements"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        return (
            Announcement.objects.filter(author=user)
            .select_related("author")
            .prefetch_related("target_groups", "target_members")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        qs = self.get_queryset()
        priority_map = {
            "urgent": {"label": "Urgent", "color": "danger"},
            "high": {"label": "High", "color": "warning"},
            "normal": {"label": "Normal", "color": "primary"},
            "low": {"label": "Low", "color": "secondary"},
        }

        counts = Counter(qs.values_list("priority", flat=True))

        priority_stats = []
        for code, meta in priority_map.items():
            priority_stats.append(
                {
                    "code": code,
                    "label": meta["label"],
                    "color": meta["color"],
                    "count": counts.get(code, 0),
                }
            )
        context.update(
            {
                "all_announcements": qs,
                "published_announcements": qs.filter(
                    is_published=True, publish_at__lte=now
                ),
                "scheduled_announcements": qs.filter(
                    is_published=True, publish_at__gt=now
                ),
                "draft_announcements": qs.filter(is_published=False),
                "expired_announcements": qs.filter(expires_at__lt=now),
                "total_announcements": qs.count(),
                "published_count": qs.filter(
                    is_published=True, publish_at__lte=now
                ).count(),
                "scheduled_count": qs.filter(
                    is_published=True, publish_at__gt=now
                ).count(),
                "drafts_count": qs.filter(is_published=False).count(),
                "expired_count": qs.filter(expires_at__lt=now).count(),
                "filter_form": AnnouncementFilterForm(self.request.GET),
                "today": now,
                "priority_stats": priority_stats,
            }
        )

        return context


class AnnouncementDashboardView(LoginRequiredMixin, TemplateView):
    """Announcement dashboard with statistics"""

    template_name = "announcements/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()

        # Overall statistics (for admins)
        if user.is_staff or user.is_superuser:
            total_announcements = Announcement.objects.count()
            total_published = Announcement.objects.filter(
                is_published=True, publish_at__lte=now
            ).count()
            total_authors = Announcement.objects.values("author").distinct().count()
        else:
            # Get announcements visible to the current member
            announcements = (
                Announcement.objects.filter(is_published=True, publish_at__lte=now)
                .filter(
                    Q(is_church_wide=True)
                    | Q(target_members=user)
                    | Q(target_groups__group_members__member=user)
                    | Q(author=user)
                )
                .distinct()
            )

            total_announcements = announcements.count()
            total_published = total_announcements
            total_authors = 1  # Only user's own announcements

        # Get user's groups
        user_group_ids = []
        if hasattr(user, "memberships"):
            user_group_ids = user.memberships.values_list("group_id", flat=True)

        # Recent announcements (last 7 days)
        week_ago = now - timezone.timedelta(days=7)
        recent_announcements = (
            Announcement.objects.filter(
                is_published=True,
                publish_at__gte=week_ago,
                publish_at__lte=now,
            )
            .filter(
                Q(is_church_wide=True)
                | Q(target_groups__in=user_group_ids)
                | Q(target_members=user)
                | Q(author=user)
            )
            .distinct()
            .order_by("-publish_at")[:3]  # LIMIT HERE ✅
        )

        # Urgent announcements
        urgent_announcements = Announcement.objects.filter(
            priority="urgent",
            is_published=True,
            publish_at__lte=now,
            expires_at__gt=now,
        ).order_by("-publish_at")[:5]

        # Upcoming announcements (scheduled)
        upcoming_announcements = Announcement.objects.filter(
            is_published=True, publish_at__gt=now
        ).order_by("publish_at")[:5]

        # Announcements by priority
        priority_stats = []
        for priority_code, priority_name in Announcement.PRIORITY_LEVELS:
            count = Announcement.objects.filter(
                priority=priority_code,
                is_published=True,
                publish_at__lte=now,
                expires_at__gt=now,
            ).count()
            priority_stats.append(
                {
                    "name": priority_name,
                    "code": priority_code,
                    "count": count,
                    "color": self.get_priority_color(priority_code),
                }
            )

        # User's group announcements
        user_groups = []
        if hasattr(user, "memberships"):
            user_groups = user.memberships.values_list("group__name", flat=True)

        context.update(
            {
                "total_announcements": total_announcements,
                "total_published": total_published,
                "total_authors": total_authors,
                "recent_announcements": recent_announcements,
                "urgent_announcements": urgent_announcements,
                "upcoming_announcements": upcoming_announcements,
                "priority_stats": priority_stats,
                "user_groups": user_groups,
                "can_create": self.can_create_announcement(user),
                "today": now.date(),
            }
        )

        return context

    def get_priority_color(self, priority_code):
        """Get Bootstrap color for priority level"""
        colors = {
            "urgent": "danger",
            "high": "warning",
            "normal": "primary",
            "low": "secondary",
        }
        return colors.get(priority_code, "secondary")

    def can_create_announcement(self, user):
        """Check if user can create announcements"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return True

            if user.church_role.can_send_announcements:
                return True

        return False


# API Views
class AnnouncementStatisticsView(LoginRequiredMixin, TemplateView):
    """Get announcement statistics (JSON)"""

    def get(self, request, *args, **kwargs):
        user = request.user
        now = timezone.now()

        # Base statistics
        stats = {
            "total": 0,
            "published": 0,
            "scheduled": 0,
            "drafts": 0,
            "expired": 0,
            "by_priority": {},
            "by_day": {},
            "recent": [],
        }

        # Determine which announcements to count
        if user.is_staff or user.is_superuser:
            queryset = Announcement.objects.all()
        else:
            # User can only see announcements they authored or are targeted to them
            user_groups = []
            if hasattr(user, "memberships"):
                user_groups = user.memberships.values_list("group", flat=True)

            visible_ids = []
            all_announcements = Announcement.objects.all()

            for announcement in all_announcements:
                if announcement.author == user:
                    visible_ids.append(announcement.id)
                elif announcement.is_church_wide:
                    visible_ids.append(announcement.id)
                elif announcement.target_groups.filter(id__in=user_groups).exists():
                    visible_ids.append(announcement.id)
                elif announcement.target_members.filter(id=user.id).exists():
                    visible_ids.append(announcement.id)

            queryset = Announcement.objects.filter(id__in=visible_ids)

        # Calculate statistics
        stats["total"] = queryset.count()
        stats["published"] = queryset.filter(
            is_published=True, publish_at__lte=now
        ).count()
        stats["scheduled"] = queryset.filter(
            is_published=True, publish_at__gt=now
        ).count()
        stats["drafts"] = queryset.filter(is_published=False).count()
        stats["expired"] = queryset.filter(expires_at__lt=now).count()

        # Statistics by priority
        for priority_code, priority_name in Announcement.PRIORITY_LEVELS:
            count = queryset.filter(
                priority=priority_code,
                is_published=True,
                publish_at__lte=now,
                expires_at__gt=now,
            ).count()
            stats["by_priority"][priority_name] = count

        # Statistics by day (last 30 days)
        thirty_days_ago = now - timezone.timedelta(days=30)
        announcements_by_day = (
            queryset.filter(publish_at__gte=thirty_days_ago, publish_at__lte=now)
            .extra({"day": "DATE(publish_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        for item in announcements_by_day:
            stats["by_day"][item["day"]] = item["count"]

        # Recent announcements
        recent = (
            queryset.filter(is_published=True, publish_at__lte=now)
            .order_by("-publish_at")[:5]
            .values("id", "title", "priority", "publish_at")
        )

        stats["recent"] = list(recent)

        return JsonResponse(stats)
