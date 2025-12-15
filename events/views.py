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
    View,
)
from django.db.models import Q, Count
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.models import Group  # Django's built-in Group

from core.mixins import AdminRequiredMixin, GroupLeaderRequiredMixin
from .models import Event, EventRegistration
from .forms import EventForm, EventRegistrationForm, EventFilterForm
from groups.models import ChurchGroup, Membership, UserRole
from accounts.models import CustomUser


class EventListView(LoginRequiredMixin, ListView):
    """List all events"""

    model = Event
    template_name = "events/list.html"
    context_object_name = "events"
    paginate_by = 12

    def get_queryset(self):
        user = self.request.user

        # get user's group IDS

        user_group_ids = Membership.objects.filter(member=user).values_list(
            "group_id", flat=True
        )

        # BASE visibility rules

        queryset = Event.objects.filter(
            Q(is_church_wide=True)
            | Q(allowed_groups__id__in=user_group_ids)
            | Q(allowed_members=user)
            | Q(assigned_to__id__in=user_group_ids)
        ).distinct()

        # Apply filters from form
        form = EventFilterForm(self.request.GET)
        if form.is_valid():
            event_type = form.cleaned_data.get("event_type")
            start_date = form.cleaned_data.get("start_date")
            end_date = form.cleaned_data.get("end_date")
            is_church_wide = form.cleaned_data.get("is_church_wide")
            group = form.cleaned_data.get("group")

            if event_type:
                queryset = queryset.filter(event_type=event_type)

            if start_date:
                queryset = queryset.filter(start_datetime__date__gte=start_date)

            if end_date:
                queryset = queryset.filter(start_datetime__date__lte=end_date)

            if is_church_wide == "yes":
                queryset = queryset.filter(is_church_wide=True)
            elif is_church_wide == "no":
                queryset = queryset.filter(is_church_wide=False)

            if group:
                queryset = queryset.filter(
                    Q(assigned_to=group) | Q(allowed_groups=group)
                )

        return queryset

    def get_base_queryset(self):
        user = self.request.user
        user_group_ids = Membership.objects.filter(member=user).values_list(
            "group_id", flat=True
        )

        return Event.objects.filter(
            Q(is_church_wide=True)
            | Q(allowed_groups__id__in=user_group_ids)
            | Q(allowed_members=user)
            | Q(assigned_to__id__in=user_group_ids)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        base_qs = self.get_base_queryset()

        context["filter_form"] = EventFilterForm(self.request.GET)
        context["upcoming_events"] = Event.objects.filter(
            start_datetime__gte=now
        ).order_by("start_datetime")[:5]
        context["past_events"] = Event.objects.filter(start_datetime__lt=now).order_by(
            "-start_datetime"
        )[:5]
        context["now"] = now
        context["ongoing_events"] = Event.objects.filter(
            start_datetime__lte=now,
            end_datetime__gte=now,
        ).order_by("start_datetime")
        return context


class EventCalendarView(LoginRequiredMixin, TemplateView):
    """Calendar view of events"""

    template_name = "events/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # We'll add FullCalendar integration later
        context["events"] = Event.objects.filter(
            start_datetime__gte=timezone.now() - timezone.timedelta(days=30),
            start_datetime__lte=timezone.now() + timezone.timedelta(days=60),
        )
        return context


class EventDetailView(LoginRequiredMixin, DetailView):
    """View event details"""

    model = Event
    template_name = "events/detail.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object

        # Check if user can register
        context["can_register"] = self.can_register(event)

        # Check if user is already registered
        if self.request.user.is_authenticated:
            try:
                registration = EventRegistration.objects.get(
                    event=event, member=self.request.user
                )
                context["user_registration"] = registration
                context["is_registered"] = True
            except EventRegistration.DoesNotExist:
                context["is_registered"] = False

        # Get registrations if user has permission
        if self.can_view_registrations(event):
            context["registrations"] = (
                EventRegistration.objects.filter(event=event)
                .select_related("member")
                .order_by("-registered_at")
            )
            context["registration_count"] = context["registrations"].count()

        # Get attendance statistics
        context["attendance_stats"] = self.get_attendance_stats(event)
        context["now"] = timezone.now()

        return context

    def can_register(self, event):
        """Check if current user can register for this event"""
        if not self.request.user.is_authenticated:
            return False

        if not event.requires_registration:
            return False

        # Check registration deadline
        if event.registration_deadline and timezone.now() > event.registration_deadline:
            return False

        # Check capacity
        if event.capacity:
            current_registrations = EventRegistration.objects.filter(
                event=event
            ).count()
            if current_registrations >= event.capacity:
                return False

        # Check if user is allowed
        if event.is_church_wide:
            return True

        # Check group membership through ChurchGroup
        user_church_groups = set()
        if hasattr(self.request.user, "memberships"):
            user_church_groups = set(
                self.request.user.memberships.values_list("group", flat=True)
            )

        # Check if user is in allowed ChurchGroups
        if event.allowed_groups.exists():
            allowed_group_ids = set(event.allowed_groups.values_list("id", flat=True))
            if user_church_groups.intersection(allowed_group_ids):
                return True

        # Check individual allowance
        if event.allowed_members.filter(id=self.request.user.id).exists():
            return True

        # Check if assigned to user's ChurchGroup
        if event.assigned_to and hasattr(self.request.user, "memberships"):
            if Membership.objects.filter(
                member=self.request.user, group=event.assigned_to
            ).exists():
                return True

        return False

    def can_view_registrations(self, event):
        """Check if user can view event registrations"""
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return True

        # Check UserRole permissions
        if hasattr(user, "church_role"):
            church_role = user.church_role

            if church_role.role_type in ["super_admin", "church_admin"]:
                return True

            if church_role.can_manage_events:
                return True

            # Check if user is organizer
            if event.organizer == user:
                return True

            # Check if user is a leader of the assigned ChurchGroup
            if event.assigned_to and hasattr(user, "leading_groups"):
                if event.assigned_to in user.leading_groups.all():
                    return True

        return False

    def get_attendance_stats(self, event):
        """Get attendance statistics for event"""
        total_registered = EventRegistration.objects.filter(event=event).count()
        total_attended = EventRegistration.objects.filter(
            event=event, attended=True
        ).count()

        stats = {
            "total_registered": total_registered,
            "total_attended": total_attended,
            "attendance_rate": 0,
        }

        if total_registered > 0:
            stats["attendance_rate"] = (total_attended / total_registered) * 100

        return stats


class EventCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new event"""

    model = Event
    form_class = EventForm
    template_name = "events/form.html"
    success_message = "Event created successfully!"

    def get_success_url(self):
        return reverse_lazy("events:detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if not form.instance.organizer:
            form.instance.organizer = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create New Event"
        context["submit_text"] = "Create Event"
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to create events
        user = request.user

        if not user.is_authenticated:
            return self.handle_no_permission()

        # Allow admins and users with event management permission
        if user.is_staff or user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
                "group_leader",
            ]:
                return super().dispatch(request, *args, **kwargs)

            if user.church_role.can_manage_events:
                return super().dispatch(request, *args, **kwargs)

        messages.error(request, "You don't have permission to create events.")
        return redirect("events:list")


class EventUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update an existing event"""

    model = Event
    form_class = EventForm
    template_name = "events/form.html"
    success_message = "Event updated successfully!"

    def get_success_url(self):
        return reverse_lazy("events:detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Event: {self.object.title}"
        context["submit_text"] = "Update Event"
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to update this event
        self.object = self.get_object()
        user = request.user

        if not user.is_authenticated:
            return self.handle_no_permission()

        # Allow admins and users with event management permission
        if user.is_staff or user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return super().dispatch(request, *args, **kwargs)

            if user.church_role.can_manage_events:
                return super().dispatch(request, *args, **kwargs)

            # Check if user is organizer
            if self.object.organizer == user:
                return super().dispatch(request, *args, **kwargs)

            # Check if user is a leader of the assigned ChurchGroup
            if self.object.assigned_to and hasattr(user, "leading_groups"):
                if self.object.assigned_to in user.leading_groups.all():
                    return super().dispatch(request, *args, **kwargs)

        messages.error(request, "You don't have permission to edit this event.")
        return redirect("events:detail", pk=self.object.pk)


class EventDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete an event"""

    model = Event
    template_name = "events/confirm_delete.html"
    success_url = reverse_lazy("events:list")
    success_message = "Event deleted successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registrations_count"] = EventRegistration.objects.filter(
            event=self.object
        ).count()
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to delete this event
        self.object = self.get_object()
        user = request.user

        if not user.is_authenticated:
            return self.handle_no_permission()

        # Only allow admins to delete events
        if user.is_staff or user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return super().dispatch(request, *args, **kwargs)

        messages.error(request, "You don't have permission to delete events.")
        return redirect("events:detail", pk=self.object.pk)


class EventRegisterView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Register for an event"""

    model = EventRegistration
    form_class = EventRegistrationForm
    template_name = "events/register.html"

    def get_success_url(self):
        return reverse_lazy("events:detail", kwargs={"pk": self.kwargs["pk"]})

    def get_success_message(self, cleaned_data):
        return "Successfully registered for the event!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        event = get_object_or_404(Event, pk=self.kwargs["pk"])
        kwargs["event"] = event
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        event = get_object_or_404(Event, pk=self.kwargs["pk"])

        # Double-check capacity
        if event.capacity:
            current_registrations = EventRegistration.objects.filter(
                event=event
            ).count()
            if current_registrations >= event.capacity:
                messages.error(self.request, "Event has reached maximum capacity.")
                return redirect("events:detail", pk=event.pk)

        form.instance.event = event
        form.instance.member = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = get_object_or_404(Event, pk=self.kwargs["pk"])
        context["event"] = event

        # Check if already registered
        try:
            EventRegistration.objects.get(event=event, member=self.request.user)
            context["already_registered"] = True
        except EventRegistration.DoesNotExist:
            context["already_registered"] = False

        return context


class EventUnregisterView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Unregister from an event"""

    model = EventRegistration
    template_name = "events/unregister.html"

    def get_success_url(self):
        return reverse_lazy("events:detail", kwargs={"pk": self.object.event.pk})

    def get_success_message(self, cleaned_data):
        return "Successfully unregistered from the event!"

    def get_object(self):
        event = get_object_or_404(Event, pk=self.kwargs["pk"])
        return get_object_or_404(
            EventRegistration, event=event, member=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.object.event
        return context


class EventRegistrationsView(LoginRequiredMixin, DetailView):
    """View event registrations (admin/organizer only)"""

    model = Event
    template_name = "events/registrations.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object

        # Check permissions
        if not self.has_permission(event):
            messages.error(
                self.request, "You don't have permission to view registrations."
            )
            return context

        # Get all registrations
        registrations = (
            EventRegistration.objects.filter(event=event)
            .select_related("member")
            .order_by("-registered_at")
        )

        context["registrations"] = registrations
        context["total_registered"] = registrations.count()
        context["total_attended"] = registrations.filter(attended=True).count()

        return context

    def has_permission(self, event):
        """Check if user can view registrations"""
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return True

            if user.church_role.can_manage_events:
                return True

            # Check if user is organizer
            if event.organizer == user:
                return True

            # Check if user is a leader of the assigned ChurchGroup
            if event.assigned_to and hasattr(user, "leading_groups"):
                if event.assigned_to in user.leading_groups.all():
                    return True

        return False


class UpdateAttendanceView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update attendance for a registration"""

    model = EventRegistration
    fields = ["attended", "notes"]
    template_name = "events/update_attendance.html"

    def get_success_url(self):
        return reverse_lazy("events:registrations", kwargs={"pk": self.object.event.pk})

    def get_success_message(self, cleaned_data):
        return f"Attendance updated for {self.object.member.get_full_name()}!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.object.event
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to update attendance
        self.object = self.get_object()
        user = request.user

        if not user.is_authenticated:
            return self.handle_no_permission()

        # Check permissions for this specific event
        event = self.object.event

        if user.is_staff or user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return super().dispatch(request, *args, **kwargs)

            if user.church_role.can_manage_events:
                return super().dispatch(request, *args, **kwargs)

            # Check if user is organizer
            if event.organizer == user:
                return super().dispatch(request, *args, **kwargs)

            # Check if user is a leader of the assigned ChurchGroup
            if event.assigned_to and hasattr(user, "leading_groups"):
                if event.assigned_to in user.leading_groups.all():
                    return super().dispatch(request, *args, **kwargs)

        messages.error(request, "You don't have permission to update attendance.")
        return redirect("events:detail", pk=event.pk)


class MyEventsView(LoginRequiredMixin, TemplateView):
    """View events the user is registered for"""

    template_name = "events/my_events.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get events user is registered for
        registrations = (
            EventRegistration.objects.filter(member=user)
            .select_related("event")
            .order_by("-event__start_datetime")
        )

        context["registrations"] = registrations

        # Split into upcoming and past
        now = timezone.now()
        context["upcoming_registrations"] = [
            reg for reg in registrations if reg.event.start_datetime >= now
        ]
        context["past_registrations"] = [
            reg for reg in registrations if reg.event.start_datetime < now
        ]

        # Get events organized by user
        context["organized_events"] = Event.objects.filter(organizer=user).order_by(
            "-start_datetime"
        )

        # Get events assigned to user's ChurchGroups
        if hasattr(user, "memberships"):
            # Get user's ChurchGroup IDs
            user_church_group_ids = user.memberships.values_list("group", flat=True)

            # Get events assigned to these ChurchGroups
            context["group_events"] = (
                Event.objects.filter(
                    Q(assigned_to__in=user_church_group_ids)
                    | Q(allowed_groups__in=user_church_group_ids)
                )
                .distinct()
                .order_by("-start_datetime")
            )
        else:
            context["group_events"] = Event.objects.none()

        return context


# API Views
class EventCalendarDataView(LoginRequiredMixin, View):
    """JSON data for calendar"""

    def get(self, request, *args, **kwargs):
        events = Event.objects.all()

        calendar_events = []
        for event in events:
            calendar_events.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "start": event.start_datetime.isoformat(),
                    "end": event.end_datetime.isoformat(),
                    "url": reverse_lazy("events:detail", kwargs={"pk": event.id}),
                    "color": self.get_event_color(event.event_type),
                    "textColor": "white",
                    "extendedProps": {
                        "type": event.get_event_type_display(),
                        "location": event.location,
                        "description": (
                            event.description[:100] + "..."
                            if len(event.description) > 100
                            else event.description
                        ),
                    },
                }
            )

        return JsonResponse(calendar_events, safe=False)

    def get_event_color(self, event_type):
        """Get color for event type"""
        colors = {
            "service": "#3498db",  # Blue
            "meeting": "#2ecc71",  # Green
            "fellowship": "#9b59b6",  # Purple
            "outreach": "#e74c3c",  # Red
            "training": "#f39c12",  # Orange
            "celebration": "#1abc9c",  # Teal
        }
        return colors.get(event_type, "#95a5a6")  # Default gray
