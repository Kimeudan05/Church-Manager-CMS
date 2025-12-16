from django.contrib import admin
from .models import Project, Task


class TaskInline(admin.TabularInline):
    """Inline task editor for projects"""

    model = Task
    extra = 1
    fields = ("title", "assigned_to", "due_date", "priority", "status")
    readonly_fields = ("created_at", "updated_at")


class ProjectAdmin(admin.ModelAdmin):
    """Admin configuration for Project"""

    list_display = (
        "title",
        "responsible_group",
        "project_leader",
        "status",
        "progress_percentage",
        "start_date",
        "target_end_date",
    )
    list_filter = ("status", "project_type", "responsible_group", "start_date")
    search_fields = ("title", "description", "responsible_group__name")
    readonly_fields = ("created_at", "updated_at", "actual_end_date")
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "description", "project_type", "status")},
        ),
        (
            "Organization",
            {"fields": ("responsible_group", "project_leader", "team_members")},
        ),
        (
            "Timeline",
            {
                "fields": (
                    "start_date",
                    "target_end_date",
                    "actual_end_date",
                    "progress_percentage",
                )
            },
        ),
        (
            "Budget",
            {"fields": ("budget_amount", "actual_spent"), "classes": ("collapse",)},
        ),
        ("Planning", {"fields": ("milestones",), "classes": ("collapse",)}),
        (
            "System Information",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    inlines = [TaskInline]
    filter_horizontal = ("team_members",)

    def save_model(self, request, obj, form, change):
        # Auto-set actual_end_date if status is changed to completed
        if obj.status == "completed" and not obj.actual_end_date:
            from django.utils import timezone

            obj.actual_end_date = timezone.now().date()
        super().save_model(request, obj, form, change)


class TaskAdmin(admin.ModelAdmin):
    """Admin configuration for Task"""

    list_display = (
        "title",
        "project",
        "assigned_to",
        "status",
        "priority",
        "due_date",
        "completed_at",
    )
    list_filter = ("status", "priority", "project", "assigned_to")
    search_fields = ("title", "description", "project__title")
    readonly_fields = ("created_at", "updated_at", "completed_at")
    fieldsets = (
        ("Task Information", {"fields": ("title", "description", "project")}),
        ("Assignment", {"fields": ("assigned_to", "assigned_by")}),
        ("Timeline", {"fields": ("due_date", "completed_at")}),
        ("Status", {"fields": ("priority", "status")}),
        (
            "System Information",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        # Auto-set completed_at if status is changed to completed
        if obj.status == "completed" and not obj.completed_at:
            from django.utils import timezone

            obj.completed_at = timezone.now().date()

        # Set assigned_by if not set
        if not obj.assigned_by:
            obj.assigned_by = request.user

        super().save_model(request, obj, form, change)


admin.site.register(Project, ProjectAdmin)
admin.site.register(Task, TaskAdmin)
