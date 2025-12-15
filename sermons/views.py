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
from django.http import JsonResponse, FileResponse
from django.db.models.functions import ExtractYear, ExtractMonth

from core.mixins import AdminRequiredMixin
from .models import Sermon
from .forms import SermonForm, SermonFilterForm, SermonSearchForm
import calendar


class SermonListView(ListView):
    """List all sermons"""

    model = Sermon
    template_name = "sermons/list.html"
    context_object_name = "sermons"
    paginate_by = 12

    def get_queryset(self):
        queryset = Sermon.objects.all().select_related("preacher", "created_by")

        # Apply filters from form
        form = SermonFilterForm(self.request.GET)
        if form.is_valid():
            preacher_type = form.cleaned_data.get("preacher_type")
            sermon_type = form.cleaned_data.get("sermon_type")
            start_date = form.cleaned_data.get("start_date")
            end_date = form.cleaned_data.get("end_date")
            has_media = form.cleaned_data.get("has_media")
            search = form.cleaned_data.get("search")
            series = form.cleaned_data.get("series")

            if preacher_type == "member":
                queryset = queryset.filter(preacher__isnull=False)
            elif preacher_type == "guest":
                queryset = queryset.filter(guest_speaker_name__isnull=False)

            if sermon_type:
                queryset = queryset.filter(sermon_type=sermon_type)

            if start_date:
                queryset = queryset.filter(sermon_date__gte=start_date)

            if end_date:
                queryset = queryset.filter(sermon_date__lte=end_date)

            if has_media == "yes":
                queryset = queryset.filter(
                    Q(audio_file__isnull=False)
                    | Q(video_url__isnull=False)
                    | Q(slides_file__isnull=False)
                    | Q(handout_file__isnull=False)
                )
            elif has_media == "no":
                queryset = queryset.filter(
                    audio_file__isnull=True,
                    video_url__isnull=True,
                    slides_file__isnull=True,
                    handout_file__isnull=True,
                )

            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search)
                    | Q(summary__icontains=search)
                    | Q(scripture_reference__icontains=search)
                    | Q(preacher__first_name__icontains=search)
                    | Q(preacher__last_name__icontains=search)
                    | Q(guest_speaker_name__icontains=search)
                    | Q(tags__icontains=search)
                )

            if series:
                queryset = queryset.filter(series__icontains=series)

        return queryset.order_by("-sermon_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = SermonFilterForm(self.request.GET)
        context["search_form"] = SermonSearchForm(self.request.GET)

        # Get sermon statistics
        context["total_sermons"] = Sermon.objects.count()
        context["recent_sermons"] = Sermon.objects.filter(
            sermon_date__gte=timezone.now().date() - timezone.timedelta(days=30)
        ).count()

        # Add can_upload variable
        context["can_upload"] = self.request.user.has_perm("sermons.can_upload_sermons")

        # Get unique preachers count
        member_preachers = (
            Sermon.objects.filter(preacher__isnull=False)
            .values("preacher")
            .distinct()
            .count()
        )
        guest_preachers = (
            Sermon.objects.filter(guest_speaker_name__isnull=False)
            .values("guest_speaker_name")
            .distinct()
            .count()
        )
        context["total_preachers"] = member_preachers + guest_preachers

        # Get most common sermon types
        sermon_types = (
            Sermon.objects.values("sermon_type")
            .annotate(count=Count("sermon_type"))
            .order_by("-count")[:5]
        )
        context["sermon_types"] = sermon_types

        # Get series list
        series_list = (
            Sermon.objects.exclude(series="")
            .values_list("series", flat=True)
            .distinct()
        )
        context["series_list"] = series_list[:10]

        return context


class SermonDetailView(DetailView):
    """View sermon details"""

    model = Sermon
    template_name = "sermons/detail.html"
    context_object_name = "sermon"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sermon = self.object

        # Get related sermons (same preacher or series)
        related_sermons = (
            Sermon.objects.filter(
                Q(preacher=sermon.preacher)
                | Q(series=sermon.series)
                | Q(sermon_type=sermon.sermon_type)
            )
            .exclude(pk=sermon.pk)
            .order_by("-sermon_date")[:4]
        )

        context["related_sermons"] = related_sermons
        context["media_count"] = sermon.get_media_count()

        # Check if user can edit/delete
        user = self.request.user
        context["can_edit"] = self.can_edit_sermon(user, sermon)
        context["can_delete"] = self.can_delete_sermon(user, sermon)

        # for the video url
        # Vimeo video ID
        import re

        vimeo_id = None
        if "vimeo.com" in sermon.video_url:
            match = re.search(r"vimeo\.com/(\d+)", sermon.video_url)
            if match:
                vimeo_id = match.group(1)
        context["vimeo_id"] = vimeo_id

        # for youtube
        from urllib.parse import urlparse, parse_qs

        youtube_id = None
        if "youtube.com" in sermon.video_url:
            parsed_url = urlparse(sermon.video_url)
            query = parse_qs(parsed_url.query)
            youtube_id = query.get("v", [None])[0]  # This gets only the video ID
        elif "youtu.be" in sermon.video_url:
            youtube_id = sermon.video_url.rstrip("/").split("/")[-1]

        context["youtube_id"] = youtube_id
        return context

    def can_edit_sermon(self, user, sermon):
        """Check if user can edit this sermon"""
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

            if user.church_role.can_manage_events:  # Using event permission for now
                return True

            # Check if user created the sermon
            if sermon.created_by == user:
                return True

        return False

    def can_delete_sermon(self, user, sermon):
        """Check if user can delete this sermon"""
        if not user.is_authenticated:
            return False

        # Only admins can delete sermons
        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return True

        return False


class SermonCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new sermon"""

    model = Sermon
    form_class = SermonForm
    template_name = "sermons/form.html"
    success_message = "Sermon created successfully!"

    def get_success_url(self):
        return reverse_lazy("sermons:detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Upload New Sermon"
        context["submit_text"] = "Upload Sermon"
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to create sermons
        user = request.user

        if not user.is_authenticated:
            return self.handle_no_permission()

        # Allow admins and users with sermon management permission
        if user.is_staff or user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return super().dispatch(request, *args, **kwargs)

            # Check custom permission for sermons
            if hasattr(user.church_role, "permissions_granted"):
                if user.church_role.permissions_granted.filter(
                    codename="can_upload_sermons"
                ).exists():
                    return super().dispatch(request, *args, **kwargs)

        messages.error(request, "You don't have permission to upload sermons.")
        return redirect("sermons:list")


class SermonUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update an existing sermon"""

    model = Sermon
    form_class = SermonForm
    template_name = "sermons/form.html"
    success_message = "Sermon updated successfully!"

    def get_success_url(self):
        return reverse_lazy("sermons:detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Sermon: {self.object.title}"
        context["submit_text"] = "Update Sermon"
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to edit this sermon
        self.object = self.get_object()
        user = request.user

        if not user.is_authenticated:
            return self.handle_no_permission()

        # Allow admins and users with sermon management permission
        if user.is_staff or user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return super().dispatch(request, *args, **kwargs)

            # Check if user created the sermon
            if self.object.created_by == user:
                return super().dispatch(request, *args, **kwargs)

        messages.error(request, "You don't have permission to edit this sermon.")
        return redirect("sermons:detail", pk=self.object.pk)


class SermonDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete a sermon"""

    model = Sermon
    template_name = "sermons/confirm_delete.html"
    success_url = reverse_lazy("sermons:list")
    success_message = "Sermon deleted successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["media_count"] = self.object.get_media_count()
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to delete sermons
        self.object = self.get_object()
        user = request.user

        if not user.is_authenticated:
            return self.handle_no_permission()

        # Only allow admins to delete sermons
        if user.is_staff or user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return super().dispatch(request, *args, **kwargs)

        messages.error(request, "You don't have permission to delete sermons.")
        return redirect("sermons:detail", pk=self.object.pk)


class SermonArchiveView(ListView):
    """Archive view organized by year/month"""

    model = Sermon
    template_name = "sermons/archive.html"
    context_object_name = "sermons"

    def get_queryset(self):
        queryset = Sermon.objects.all()
        year = self.kwargs.get("year")
        month = self.kwargs.get("month")

        if year:
            queryset = queryset.filter(sermon_date__year=year)
            if month:
                queryset = queryset.filter(sermon_date__month=month)

        return queryset.order_by("-sermon_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get archive years with counts
        archive_years = (
            Sermon.objects.annotate(year=ExtractYear("sermon_date"))
            .values("year")
            .distinct()
            .order_by("-year")
        )
        years_with_counts = []
        for y in archive_years:
            count = Sermon.objects.filter(sermon_date__year=y["year"]).count()
            years_with_counts.append({"year": y["year"], "count": count})
        context["archive_years"] = years_with_counts

        year = self.kwargs.get("year")
        if year:
            year = int(year)
            context["current_year"] = year
            # Months for this year
            archive_months = (
                Sermon.objects.filter(sermon_date__year=year)
                .annotate(month=ExtractMonth("sermon_date"))
                .values("month")
                .distinct()
                .order_by("month")
            )
            months_with_counts = []
            for m in archive_months:
                count = Sermon.objects.filter(
                    sermon_date__year=year, sermon_date__month=m["month"]
                ).count()
                months_with_counts.append(
                    {
                        "number": m["month"],
                        "name": calendar.month_name[m["month"]],
                        "count": count,
                    }
                )
            context["archive_months"] = months_with_counts

        month = self.kwargs.get("month")
        if month:
            month = int(month)
            context["current_month"] = month
            # get month name
            month_name = next(
                (
                    m["name"]
                    for m in context.get("archive_months", [])
                    if m["number"] == month
                ),
                None,
            )
            context["current_month_name"] = month_name

        # Overall total sermons
        context["total_sermons"] = Sermon.objects.count()
        if year:
            context["total_for_year"] = Sermon.objects.filter(
                sermon_date__year=year
            ).count()

        # Count unique preachers for the current queryset
        unique_preachers_count = (
            self.get_queryset().values_list("preacher", flat=True).distinct().count()
        )
        context["unique_preachers_count"] = unique_preachers_count

        # Count sermons with media (video/audio)
        media_sermons_count = (
            self.get_queryset().exclude(video_url="").count()
        )  # or adjust for audio
        context["media_sermons_count"] = media_sermons_count

        return context


class SermonSeriesView(ListView):
    """View sermons in a series"""

    model = Sermon
    template_name = "sermons/series.html"
    context_object_name = "sermons"

    def get_queryset(self):
        series_name = self.kwargs.get("series_name")
        return Sermon.objects.filter(series__iexact=series_name).order_by(
            "series_part", "sermon_date"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series_name = self.kwargs.get("series_name")

        context["series_name"] = series_name
        context["series_count"] = self.get_queryset().count()

        # Get all series for sidebar
        all_series = (
            Sermon.objects.exclude(series="")
            .values_list("series", flat=True)
            .distinct()
            .order_by("series")
        )
        context["all_series"] = all_series

        return context


class SermonDownloadView(LoginRequiredMixin, DetailView):
    """Handle sermon file downloads"""

    model = Sermon

    def get(self, request, *args, **kwargs):
        sermon = self.get_object()
        file_type = kwargs.get("file_type")

        if file_type == "audio" and sermon.audio_file:
            return FileResponse(sermon.audio_file.open(), as_attachment=True)
        elif file_type == "slides" and sermon.slides_file:
            return FileResponse(sermon.slides_file.open(), as_attachment=True)
        elif file_type == "handout" and sermon.handout_file:
            return FileResponse(sermon.handout_file.open(), as_attachment=True)
        else:
            messages.error(request, "File not available.")
            return redirect("sermons:detail", pk=sermon.pk)


# API Views
class SermonStatisticsView(LoginRequiredMixin, TemplateView):
    """Get sermon statistics (JSON)"""

    def get(self, request, *args, **kwargs):
        import calendar
        from django.db.models.functions import ExtractYear, ExtractMonth

        # Get basic statistics
        stats = {
            "total_sermons": Sermon.objects.count(),
            "total_with_audio": Sermon.objects.filter(audio_file__isnull=False).count(),
            "total_with_video": Sermon.objects.filter(video_url__isnull=False).count(),
            "total_with_notes": Sermon.objects.filter(full_notes__isnull=False).count(),
            "by_type": {},
            "by_year": {},
        }

        # Statistics by sermon type
        sermon_types = (
            Sermon.objects.values("sermon_type")
            .annotate(count=Count("sermon_type"))
            .order_by("-count")
        )

        for item in sermon_types:
            stats["by_type"][item["sermon_type"]] = item["count"]

        # Statistics by year
        sermons_by_year = (
            Sermon.objects.annotate(year=ExtractYear("sermon_date"))
            .values("year")
            .annotate(count=Count("id"))
            .order_by("year")
        )

        for item in sermons_by_year:
            stats["by_year"][item["year"]] = item["count"]

        # Recent sermons (last 6 months)
        six_months_ago = timezone.now().date() - timezone.timedelta(days=180)
        recent_sermons = Sermon.objects.filter(sermon_date__gte=six_months_ago).values(
            "sermon_date", "title", "preacher__first_name", "preacher__last_name"
        )

        stats["recent_sermons"] = list(recent_sermons[:10])

        return JsonResponse(stats)
