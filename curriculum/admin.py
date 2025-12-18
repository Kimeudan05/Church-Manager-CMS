from django.contrib import admin
from .models import Curriculum, Lesson, LessonAttendance, CurriculumProgress


@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "curriculum_type",
        "target_group",
        "start_date",
        "end_date",
        "status",
        "progress_percentage",
        "created_by",
    )
    list_filter = ("curriculum_type", "status", "start_date", "target_group")
    search_fields = ("title", "description", "target_group__name")
    readonly_fields = ("created_at", "updated_at", "progress_percentage")
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "curriculum_type", "description", "target_group")},
        ),
        ("Duration", {"fields": ("start_date", "end_date", "total_lessons", "status")}),
        ("Resources", {"fields": ("resource_file", "external_link")}),
        (
            "Metadata",
            {"fields": ("created_by", "approved_by", "created_at", "updated_at")},
        ),
    )
    autocomplete_fields = ["target_group", "created_by", "approved_by"]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "curriculum",
        "lesson_number",
        "difficulty",
        "date_taught",
        "teacher",
        "attendance_count",
    )
    list_filter = ("difficulty", "date_taught", "curriculum__curriculum_type")
    search_fields = ("title", "objective", "scripture_reference")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "curriculum",
                    "lesson_number",
                    "title",
                    "objective",
                    "scripture_reference",
                    "difficulty",
                    "estimated_duration",
                )
            },
        ),
        (
            "Content",
            {
                "fields": (
                    "introduction",
                    "teacher_guide",
                    "student_materials",
                    "activities",
                    "discussion_questions",
                    "conclusion",
                )
            },
        ),
        (
            "Files",
            {
                "fields": (
                    "presentation_file",
                    "handout_file",
                    "audio_video",
                    "additional_files",
                )
            },
        ),
        (
            "Scheduling",
            {
                "fields": (
                    "scheduled_date",
                    "date_taught",
                    "teacher",
                    "attendance_count",
                )
            },
        ),
        ("Metadata", {"fields": ("created_at", "updated_at")}),
    )
    autocomplete_fields = ["curriculum", "teacher"]


@admin.register(LessonAttendance)
class LessonAttendanceAdmin(admin.ModelAdmin):
    list_display = ("lesson", "member", "attended", "recorded_by", "recorded_at")
    list_filter = ("attended", "recorded_at")
    search_fields = ("lesson__title", "member__username", "member__email")
    readonly_fields = ("recorded_at",)


@admin.register(CurriculumProgress)
class CurriculumProgressAdmin(admin.ModelAdmin):
    list_display = (
        "curriculum",
        "member",
        "current_lesson",
        "completion_percentage",
        "is_completed",
        "last_updated",
    )
    list_filter = ("is_completed", "curriculum__curriculum_type")
    search_fields = ("curriculum__title", "member__username")
    readonly_fields = ("started_at", "last_updated", "completion_percentage")
    filter_horizontal = ("completed_lessons",)
