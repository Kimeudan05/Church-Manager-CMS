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
)
from django.db.models import Q, Count, Sum, Avg
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models.functions import ExtractYear, ExtractMonth

from .models import Project, Task
from .forms import ProjectForm, TaskForm, ProjectFilterForm, TaskFilterForm
from accounts.models import CustomUser


class ProjectListView(LoginRequiredMixin, ListView):
    """List all projects"""

    model = Project
    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Project.objects.all()
            .select_related("responsible_group", "project_leader")
            .prefetch_related("team_members")
        )

        # Apply filters from form
        form = ProjectFilterForm(self.request.GET)
        if form.is_valid():
            project_type = form.cleaned_data.get("project_type")
            status = form.cleaned_data.get("status")
            responsible_group = form.cleaned_data.get("responsible_group")
            start_date_from = form.cleaned_data.get("start_date_from")
            start_date_to = form.cleaned_data.get("start_date_to")
            search = form.cleaned_data.get("search")

            if project_type:
                queryset = queryset.filter(project_type=project_type)

            if status:
                queryset = queryset.filter(status=status)

            if responsible_group:
                queryset = queryset.filter(responsible_group=responsible_group)

            if start_date_from:
                queryset = queryset.filter(start_date__gte=start_date_from)

            if start_date_to:
                queryset = queryset.filter(start_date__lte=start_date_to)

            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search)
                    | Q(description__icontains=search)
                    | Q(responsible_group__name__icontains=search)
                )

        return queryset.order_by("-start_date", "title")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = ProjectFilterForm(self.request.GET)

        # Get project statistics
        context["total_projects"] = Project.objects.count()
        context["active_projects"] = Project.objects.filter(status="ongoing").count()
        context["completed_projects"] = Project.objects.filter(
            status="completed"
        ).count()

        # Get projects by status
        status_counts = (
            Project.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        context["status_counts"] = status_counts

        # Get projects by type
        type_counts = (
            Project.objects.values("project_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        context["type_counts"] = type_counts

        # Get upcoming deadlines (projects ending in next 7 days)
        upcoming_deadline = timezone.now().date() + timezone.timedelta(days=7)
        context["upcoming_deadlines"] = Project.objects.filter(
            target_end_date__gte=timezone.now().date(),
            target_end_date__lte=upcoming_deadline,
            status__in=["planning", "ongoing"],
        ).order_by("target_end_date")[:5]

        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    """View project details"""

    model = Project
    template_name = "projects/detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        # Get project tasks
        context["tasks"] = project.tasks.all().select_related(
            "assigned_to", "assigned_by"
        )

        # Get task statistics
        task_stats = project.tasks.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
            in_progress=Count("id", filter=Q(status="in_progress")),
            blocked=Count("id", filter=Q(status="blocked")),
        )
        context["task_stats"] = task_stats

        # Calculate completion percentage based on tasks
        if task_stats["total"] > 0:
            context["tasks_completion"] = int(
                (task_stats["completed"] / task_stats["total"]) * 100
            )
        else:
            context["tasks_completion"] = 0

        # Get team members
        context["team_members"] = project.team_members.all()

        # Calculate remaining budget
        if project.budget_amount is not None and project.actual_spent is not None:
            context["budget_remaining"] = project.budget_amount - project.actual_spent
        else:
            context["budget_remaining"] = None  # Ensure None if not set

        # Check permissions
        user = self.request.user
        context["can_edit"] = self.can_edit_project(user, project)
        context["can_delete"] = self.can_delete_project(user, project)
        context["can_add_task"] = self.can_add_task(user, project)

        return context

    def can_edit_project(self, user, project):
        """Check if user can edit this project"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if user == project.project_leader:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return True

        return False

    def can_delete_project(self, user, project):
        """Check if user can delete this project"""
        if not user.is_authenticated:
            return False

        # Only admins and project leaders can delete
        if user.is_staff or user.is_superuser:
            return True

        if user == project.project_leader:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return True

        return False

    def can_add_task(self, user, project):
        """Check if user can add tasks to this project"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if user == project.project_leader:
            return True

        if user in project.team_members.all():
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return True

        return False

    def can_add_project(self, user, project):
        """Check if user can add tasks to this project"""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        if user == project.project_leader:
            return True

        if user in project.team_members.all():
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in [
                "super_admin",
                "church_admin",
                "sub_admin",
            ]:
                return True

        return False


class ProjectCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new project"""

    model = Project
    form_class = ProjectForm
    template_name = "projects/form.html"
    success_message = "Project created successfully!"

    def get_success_url(self):
        return reverse_lazy("projects:detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create New Project"
        context["submit_text"] = "Create Project"
        return context

    def form_valid(self, form):
        # Set project leader if not set
        if not form.instance.project_leader:
            form.instance.project_leader = self.request.user

        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response


class ProjectUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update an existing project"""

    model = Project
    form_class = ProjectForm
    template_name = "projects/form.html"
    success_message = "Project updated successfully!"

    def get_success_url(self):
        return reverse_lazy("projects:detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Project: {self.object.title}"
        context["submit_text"] = "Update Project"
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check permissions
        self.object = self.get_object()
        if not self.object.can_edit_project(request.user):
            messages.error(request, "You don't have permission to edit this project.")
            return redirect("projects:detail", pk=self.object.pk)
        return super().dispatch(request, *args, **kwargs)


class ProjectDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete a project"""

    model = Project
    template_name = "projects/project_confirm_delete.html"
    success_url = reverse_lazy("projects:list")
    success_message = "Project deleted successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task_count"] = self.object.tasks.count()
        context["team_member_count"] = self.object.team_members.count()
        return context

    def can_delete_project(self, user):
        """Check if user has permission to delete this project."""
        # Check if user is admin, project leader, or has proper role
        if user.is_staff or user.is_superuser:
            return True

        if user == self.object.project_leader:
            return True

        if hasattr(user, "church_role"):
            if user.church_role.role_type in ["super_admin", "church_admin"]:
                return True

        return False

    def dispatch(self, request, *args, **kwargs):
        # Check permissions
        self.object = self.get_object()
        if not self.can_delete_project(request.user):
            messages.error(request, "You don't have permission to delete this project.")
            return redirect("projects:detail", pk=self.object.pk)

        return super().dispatch(request, *args, **kwargs)


class TaskCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new task for a project"""

    model = Task
    form_class = TaskForm
    template_name = "projects/task_form.html"
    success_message = "Task created successfully!"

    def get_success_url(self):
        return reverse_lazy("projects:detail", kwargs={"pk": self.object.project.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        project_id = self.kwargs.get("project_id")
        if project_id:
            initial["project"] = get_object_or_404(Project, pk=project_id)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get("project_id")
        if project_id:
            context["project"] = get_object_or_404(Project, pk=project_id)
        context["title"] = "Add New Task"
        context["submit_text"] = "Create Task"
        return context

    def form_valid(self, form):
        # Set assigned_by to current user
        form.instance.assigned_by = self.request.user

        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response

    def dispatch(self, request, *args, **kwargs):
        # Check if user can add task to the project
        project = get_object_or_404(Project, pk=self.kwargs.get("project_id"))

        # If user is not the project leader or staff, restrict access
        if not (request.user == project.project_leader or request.user.is_staff):
            return HttpResponseForbidden(
                "You do not have permission to create a task for this project."
            )

        return super().dispatch(request, *args, **kwargs)


class TaskUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update an existing task"""

    model = Task
    form_class = TaskForm
    template_name = "projects/task_form.html"
    success_message = "Task updated successfully!"

    def get_success_url(self):
        return reverse_lazy("projects:detail", kwargs={"pk": self.object.project.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Task: {self.object.title}"
        context["submit_text"] = "Update Task"
        return context

    def form_valid(self, form):
        """Override form_valid to update project actual spent after saving task."""
        response = super().form_valid(form)

        # Update the project's actual spent
        self.object.project.update_actual_spent()

        return response

    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        project = task.project

        # Check if the user is the assigned user, project leader, or staff
        if not (
            request.user == task.assigned_to
            or request.user == project.project_leader
            or request.user.is_staff
        ):
            return HttpResponseForbidden(
                "You do not have permission to update this task."
            )

        return super().dispatch(request, *args, **kwargs)


class TaskDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete a task"""

    model = Task

    def get_success_url(self):
        return reverse_lazy("projects:detail", kwargs={"pk": self.object.project.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Task deleted successfully!")
        return super().delete(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        project = task.project

        # Check if the user is the assigned user, project leader, or staff
        if not (
            request.user == task.assigned_to
            or request.user == project.project_leader
            or request.user.is_staff
        ):
            return HttpResponseForbidden(
                "You do not have permission to delete this task."
            )

        return super().dispatch(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Project dashboard with overview"""

    template_name = "projects/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Overall statistics
        context["total_projects"] = Project.objects.count()
        context["active_projects"] = Project.objects.filter(status="ongoing").count()
        context["completed_projects"] = Project.objects.filter(
            status="completed"
        ).count()

        # Budget statistics
        budget_stats = Project.objects.aggregate(
            total_budget=Sum("budget_amount"),
            total_spent=Sum("actual_spent"),
            avg_budget=Avg("budget_amount"),
        )
        context["budget_stats"] = budget_stats

        # Task statistics
        task_stats = Task.objects.aggregate(
            total_tasks=Count("id"),
            completed_tasks=Count("id", filter=Q(status="completed")),
            overdue_tasks=Count(
                "id",
                filter=Q(
                    due_date__lt=timezone.now().date(),
                    status__in=["pending", "in_progress"],
                ),
            ),
        )
        context["task_stats"] = task_stats

        # User-specific data
        if user.is_authenticated:
            # Projects led by user
            context["user_projects"] = Project.objects.filter(
                project_leader=user
            ).order_by("-start_date")[:5]

            # Tasks assigned to user
            context["user_tasks"] = Task.objects.filter(
                assigned_to=user, status__in=["pending", "in_progress"]
            ).order_by("due_date")[:10]

            # Overdue tasks
            context["overdue_tasks"] = Task.objects.filter(
                assigned_to=user,
                due_date__lt=timezone.now().date(),
                status__in=["pending", "in_progress"],
            ).order_by("due_date")[:5]

        # Recent projects
        context["recent_projects"] = Project.objects.all().order_by("-created_at")[:5]

        # Projects by status (for chart)
        status_data = (
            Project.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        context["status_data"] = list(status_data)

        # Projects by type (for chart)
        type_data = (
            Project.objects.values("project_type")
            .annotate(count=Count("id"))
            .order_by("project_type")
        )
        context["type_data"] = list(type_data)

        return context


class CalendarView(LoginRequiredMixin, TemplateView):
    """Project calendar view"""

    template_name = "projects/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get projects for calendar
        projects = Project.objects.filter(
            Q(start_date__isnull=False) | Q(target_end_date__isnull=False)
        ).values("id", "title", "start_date", "target_end_date", "status")

        # Get tasks for calendar
        tasks = Task.objects.filter(due_date__isnull=False).values(
            "id", "title", "due_date", "priority", "status", "project__title"
        )

        context["projects_json"] = list(projects)
        context["tasks_json"] = list(tasks)

        return context


class GanttChartView(LoginRequiredMixin, TemplateView):
    """Gantt chart view for projects"""

    template_name = "projects/gantt.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get projects with tasks for Gantt chart
        projects = Project.objects.filter(
            start_date__isnull=False, target_end_date__isnull=False
        ).prefetch_related("tasks")

        gantt_data = []
        active_count = 0
        completed_count = 0

        for project in projects:
            if project.status == "ongoing":
                active_count += 1
            elif project.status == "completed":
                completed_count += 1

            project_data = {
                "id": f"project_{project.id}",
                "name": project.title,
                "start": project.start_date,
                "end": project.target_end_date,
                "progress": project.progress_percentage,
                "status": project.status,
                "tasks": [],
            }

            # Add project tasks
            for task in project.tasks.filter(due_date__isnull=False):
                task_data = {
                    "id": f"task_{task.id}",
                    "name": task.title,
                    "start": task.due_date.isoformat(),
                    "end": task.due_date.isoformat(),
                    "progress": 100 if task.status == "completed" else 50,
                    "status": task.status,
                    "dependency": f"project_{project.id}",
                }
                project_data["tasks"].append(task_data)

            gantt_data.append(project_data)

        context.update(
            {
                "gantt_data": gantt_data,
                "active_projects": active_count,
                "completed_projects": completed_count,
            }
        )
        return context


# API Views
class ProjectStatisticsView(LoginRequiredMixin, TemplateView):
    """Get project statistics (JSON)"""

    def get(self, request, *args, **kwargs):
        stats = {
            "total_projects": Project.objects.count(),
            "by_status": {},
            "by_type": {},
            "by_month": {},
            "budget_summary": {},
        }

        # Projects by status
        status_counts = Project.objects.values("status").annotate(count=Count("id"))
        for item in status_counts:
            stats["by_status"][item["status"]] = item["count"]

        # Projects by type
        type_counts = Project.objects.values("project_type").annotate(count=Count("id"))
        for item in type_counts:
            stats["by_type"][item["project_type"]] = item["count"]

        # Budget summary
        budget_summary = Project.objects.aggregate(
            total_budget=Sum("budget_amount"),
            total_spent=Sum("actual_spent"),
            avg_budget=Avg("budget_amount"),
        )
        stats["budget_summary"] = budget_summary

        # Projects by month (last 6 months)
        six_months_ago = timezone.now().date() - timezone.timedelta(days=180)
        projects_by_month = (
            Project.objects.filter(start_date__gte=six_months_ago)
            .annotate(month=ExtractMonth("start_date"), year=ExtractYear("start_date"))
            .values("year", "month")
            .annotate(count=Count("id"))
            .order_by("year", "month")
        )

        for item in projects_by_month:
            key = f"{item['year']}-{item['month']:02d}"
            stats["by_month"][key] = item["count"]

        return JsonResponse(stats)
