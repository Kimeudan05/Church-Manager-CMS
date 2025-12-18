from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
    View,
    TemplateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .models import Curriculum, Lesson, LessonAttendance, CurriculumProgress
from .forms import (
    CurriculumForm,
    LessonForm,
    LessonMarkTaughtForm,
    AttendanceForm,
    BulkAttendanceForm,
)
from groups.models import ChurchGroup
from core.mixins import (
    CurriculumAccessMixin,
    CanManageCurriculumMixin,
    LessonAccessMixin,
)


# Curriculum Views
class CurriculumListView(CurriculumAccessMixin, ListView):
    model = Curriculum
    template_name = "curriculum/curriculum_list.html"
    context_object_name = "curriculums"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtering
        curriculum_type = self.request.GET.get("type")
        status = self.request.GET.get("status")
        group = self.request.GET.get("group")
        search = self.request.GET.get("search")

        if curriculum_type:
            queryset = queryset.filter(curriculum_type=curriculum_type)
        if status:
            queryset = queryset.filter(status=status)
        if group:
            queryset = queryset.filter(target_group_id=group)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        return queryset.select_related("target_group", "created_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add filter options
        context["curriculum_types"] = Curriculum.CURRICULUM_CHOICES
        context["status_choices"] = Curriculum.STATUS_CHOICES
        context["groups"] = ChurchGroup.objects.all()

        # Calculate statistics
        queryset = self.get_queryset()
        context["active_count"] = queryset.filter(status="active").count()
        context["completed_count"] = queryset.filter(status="completed").count()
        context["draft_count"] = queryset.filter(status="draft").count()

        # User's groups for quick filter
        context["user_groups"] = self.request.user.leading_groups.all()

        return context


class CurriculumDetailView(CurriculumAccessMixin, DetailView):
    model = Curriculum
    template_name = "curriculum/curriculum_detail.html"
    context_object_name = "curriculum"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curriculum = self.object

        # Get all lessons for this curriculum
        lessons = curriculum.lessons.all().select_related("teacher")

        # Calculate statistics
        context["total_lessons"] = curriculum.total_lessons
        context["lessons_taught"] = lessons.filter(date_taught__isnull=False).count()
        context["lessons_remaining"] = (
            curriculum.total_lessons - context["lessons_taught"]
        )
        context["progress_percentage"] = curriculum.progress_percentage

        # Get upcoming lessons
        today = timezone.now().date()
        context["upcoming_lessons"] = lessons.filter(
            scheduled_date__gte=today
        ).order_by("scheduled_date")[:5]

        # Get recent attendance
        recent_lessons = lessons.filter(date_taught__isnull=False).order_by(
            "-date_taught"
        )[:5]
        context["recent_lessons"] = recent_lessons

        # Calculate average attendance
        if recent_lessons:
            total_attendance = sum(
                lesson.attendance_count
                for lesson in recent_lessons
                if lesson.attendance_count
            )
            context["avg_attendance"] = total_attendance // len(recent_lessons)
        else:
            context["avg_attendance"] = 0

        # Check if user is enrolled
        context["is_enrolled"] = CurriculumProgress.objects.filter(
            curriculum=curriculum, member=self.request.user
        ).exists()

        # Get user progress if enrolled
        if context["is_enrolled"]:
            progress = CurriculumProgress.objects.get(
                curriculum=curriculum, member=self.request.user
            )
            context["user_progress"] = progress.completion_percentage
            context["user_completed_lessons"] = progress.completed_lessons.count()

        return context


class CurriculumCreateView(CanManageCurriculumMixin, CreateView):
    model = Curriculum
    form_class = CurriculumForm
    template_name = "curriculum/curriculum_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, f'Curriculum "{form.instance.title}" created successfully!'
        )
        return response

    def get_success_url(self):
        return reverse("curriculum:detail", kwargs={"pk": self.object.pk})


class CurriculumUpdateView(CanManageCurriculumMixin, UpdateView):
    model = Curriculum
    form_class = CurriculumForm
    template_name = "curriculum/curriculum_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Curriculum "{form.instance.title}" updated successfully!'
        )
        return response

    def get_success_url(self):
        return reverse("curriculum:detail", kwargs={"pk": self.object.pk})


class CurriculumDeleteView(CanManageCurriculumMixin, DeleteView):
    model = Curriculum
    template_name = "curriculum/curriculum_confirm_delete.html"
    success_url = reverse_lazy("curriculum:list")

    def delete(self, request, *args, **kwargs):
        messages.success(
            request, f'Curriculum "{self.get_object().title}" deleted successfully!'
        )
        return super().delete(request, *args, **kwargs)


# Lesson Views
class LessonDetailView(LessonAccessMixin, DetailView):
    model = Lesson
    template_name = "curriculum/lesson_detail.html"
    context_object_name = "lesson"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.object

        # Get attendance records
        context["attendance_records"] = lesson.attendances.select_related("member")
        context["attendance_count"] = lesson.attendance_count
        context["attendance_present"] = lesson.attendances.filter(attended=True).count()
        context["attendance_absent"] = lesson.attendances.filter(attended=False).count()

        # Check if user attended
        if self.request.user.is_authenticated:
            user_attendance = lesson.attendances.filter(
                member=self.request.user
            ).first()
            context["user_attended"] = (
                user_attendance.attended if user_attendance else None
            )

        # Get next and previous lessons
        lessons = list(lesson.curriculum.lessons.order_by("lesson_number"))
        current_index = lessons.index(lesson)

        if current_index > 0:
            context["prev_lesson"] = lessons[current_index - 1]
        if current_index < len(lessons) - 1:
            context["next_lesson"] = lessons[current_index + 1]

        return context


class LessonCreateView(CanManageCurriculumMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = "curriculum/lesson_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.curriculum = get_object_or_404(Curriculum, pk=kwargs["curriculum_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["curriculum"] = self.curriculum
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["curriculum"] = self.curriculum  # <-- crucial for template
        return context

    def form_valid(self, form):
        form.instance.curriculum = self.curriculum
        messages.success(
            self.request,
            f'Lesson "{form.instance.title}" created successfully!',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "curriculum:lesson_detail",
            kwargs={"pk": self.object.pk},
        )


class LessonUpdateView(CanManageCurriculumMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = "curriculum/lesson_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["curriculum"] = self.object.curriculum
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Lesson "{form.instance.title}" updated successfully!'
        )
        return response

    def get_success_url(self):
        return reverse(
            "curriculum:lesson_detail",
            kwargs={
                "curriculum_id": self.object.curriculum.pk,
                "pk": self.object.pk,
            },
        )


class LessonDeleteView(CanManageCurriculumMixin, DeleteView):
    model = Lesson
    template_name = "curriculum/lesson_confirm_delete.html"

    def get_success_url(self):
        curriculum_id = self.object.curriculum.id
        return reverse("curriculum:detail", kwargs={"pk": curriculum_id})

    def delete(self, request, *args, **kwargs):
        messages.success(request, f"Lesson deleted successfully!")
        return super().delete(request, *args, **kwargs)


class LessonMarkTaughtView(CanManageCurriculumMixin, UpdateView):
    model = Lesson
    form_class = LessonMarkTaughtForm
    template_name = "curriculum/lesson_mark_taught.html"

    def form_valid(self, form):
        lesson = form.save(commit=False)
        lesson.date_taught = form.cleaned_data["date_taught"]
        lesson.attendance_count = form.cleaned_data["attendance_count"]
        lesson.save()

        messages.success(
            self.request, f"Lesson marked as taught on {lesson.date_taught}!"
        )
        return redirect(
            "curriculum:lesson_detail", curriculum_id=lesson.curriculum.pk, pk=lesson.pk
        )


# Attendance Views
class TakeAttendanceView(CanManageCurriculumMixin, CreateView):
    model = LessonAttendance
    form_class = AttendanceForm
    template_name = "curriculum/take_attendance.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        lesson_id = self.kwargs.get("lesson_id")
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        kwargs["lesson"] = lesson
        return kwargs

    def form_valid(self, form):
        lesson_id = self.kwargs.get("lesson_id")
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        form.instance.lesson = lesson
        form.instance.recorded_by = self.request.user

        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Attendance recorded for {form.instance.member.get_full_name()}",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson_id = self.kwargs.get("lesson_id")
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        context["lesson"] = lesson  # <-- add this
        return context

    def get_success_url(self):
        lesson_id = self.kwargs.get("lesson_id")
        curriculum_id = self.kwargs.get("curriculum_id")
        return reverse(
            "curriculum:lesson_detail",
            kwargs={"curriculum_id": curriculum_id, "pk": lesson_id},
        )


class BulkAttendanceView(CanManageCurriculumMixin, FormView):
    form_class = BulkAttendanceForm
    template_name = "curriculum/bulk_attendance.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        lesson_id = self.kwargs.get("lesson_id")
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        kwargs["lesson"] = lesson
        return kwargs

    def form_valid(self, form):
        lesson_id = self.kwargs.get("lesson_id")
        lesson = get_object_or_404(Lesson, pk=lesson_id)

        # Process attendance for each member
        group = lesson.curriculum.target_group
        members_attended = 0

        for membership in group.group_members.all():
            user = membership.member
            attended = form.cleaned_data.get(f"member_{user.id}", False)

            LessonAttendance.objects.update_or_create(
                lesson=lesson,
                member=user,  # ✅ CustomUser instance
                defaults={"attended": attended, "recorded_by": self.request.user},
            )

            if attended:  # ✅ increment the count
                members_attended += 1

        # Update lesson attendance count
        lesson.attendance_count = members_attended
        lesson.save()

        messages.success(
            self.request, f"Attendance recorded for {members_attended} members!"
        )
        return redirect("curriculum:lesson_detail", pk=lesson.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson_id = self.kwargs.get("lesson_id")
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        context["lesson"] = lesson  # ✅ make sure lesson is available
        return context


# Progress & Enrollment Views
class EnrollInCurriculumView(LoginRequiredMixin, View):
    """Enroll current user in a curriculum"""

    def post(self, request, curriculum_id):
        curriculum = get_object_or_404(Curriculum, pk=curriculum_id)

        # Check if already enrolled
        if CurriculumProgress.objects.filter(
            curriculum=curriculum, member=request.user
        ).exists():
            messages.info(request, "You are already enrolled in this curriculum")
        else:
            CurriculumProgress.objects.create(
                curriculum=curriculum, member=request.user
            )
            messages.success(request, f'Successfully enrolled in "{curriculum.title}"')

        return redirect("curriculum:detail", pk=curriculum_id)


class MarkLessonCompleteView(LoginRequiredMixin, View):
    """Mark a lesson as complete for current user"""

    def post(self, request, curriculum_id, lesson_id):
        lesson = get_object_or_404(Lesson, pk=lesson_id, curriculum_id=curriculum_id)

        # Get or create progress record
        progress, created = CurriculumProgress.objects.get_or_create(
            curriculum=lesson.curriculum, member=request.user
        )

        # Add lesson to completed lessons
        progress.completed_lessons.add(lesson)

        # Update current lesson
        next_lesson = (
            Lesson.objects.filter(
                curriculum=lesson.curriculum, lesson_number__gt=lesson.lesson_number
            )
            .order_by("lesson_number")
            .first()
        )

        progress.current_lesson = next_lesson

        # Check if curriculum is completed
        if progress.completed_lessons.count() == lesson.curriculum.total_lessons:
            progress.is_completed = True
            progress.completed_at = timezone.now()

        progress.save()

        messages.success(request, f'Lesson "{lesson.title}" marked as complete!')
        return redirect(
            "curriculum:lesson_detail",
            curriculum_id=lesson.curriculum.pk,
            pk=lesson.pk,
        )


# Dashboard & Statistics Views
class CurriculumDashboardView(CurriculumAccessMixin, TemplateView):
    template_name = "curriculum/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get all accessible curriculums
        curriculums = self.get_queryset()

        # Statistics
        context["total_curriculums"] = curriculums.count()
        context["active_curriculums"] = curriculums.filter(status="active").count()
        context["total_lessons"] = Lesson.objects.filter(
            curriculum__in=curriculums
        ).count()

        # User's enrolled curriculums
        context["enrolled_curriculums"] = CurriculumProgress.objects.filter(
            member=user
        ).select_related("curriculum")

        # Upcoming lessons
        today = timezone.now().date()
        next_week = today + timedelta(days=7)

        context["upcoming_lessons"] = (
            Lesson.objects.filter(
                curriculum__in=curriculums,
                scheduled_date__gte=today,
                scheduled_date__lte=next_week,
            )
            .select_related("curriculum", "teacher")
            .order_by("scheduled_date")[:10]
        )

        # Recent activity
        context["recent_lessons_taught"] = (
            Lesson.objects.filter(curriculum__in=curriculums, date_taught__isnull=False)
            .select_related("curriculum", "teacher")
            .order_by("-date_taught")[:10]
        )

        # Group-wise distribution
        group_stats = []
        for group in ChurchGroup.objects.all():
            count = curriculums.filter(target_group=group).count()
            if count > 0:
                group_stats.append({"group": group, "count": count})

        context["group_stats"] = sorted(
            group_stats, key=lambda x: x["count"], reverse=True
        )[:5]

        return context


class CurriculumStatisticsView(CurriculumAccessMixin, View):
    """API endpoint for curriculum statistics"""

    def get(self, request):
        curriculums = self.get_queryset()

        # Calculate statistics
        stats = {
            "by_status": dict(
                curriculums.values_list("status").annotate(count=Count("id"))
            ),
            "by_type": dict(
                curriculums.values_list("curriculum_type").annotate(count=Count("id"))
            ),
            "total_curriculums": curriculums.count(),
            "active_curriculums": curriculums.filter(status="active").count(),
            "completed_curriculums": curriculums.filter(status="completed").count(),
            "avg_lessons": curriculums.aggregate(avg=Avg("total_lessons"))["avg"] or 0,
            "total_lessons": Lesson.objects.filter(curriculum__in=curriculums).count(),
            "lessons_taught": Lesson.objects.filter(
                curriculum__in=curriculums, date_taught__isnull=False
            ).count(),
        }

        return JsonResponse(stats)
