from django.contrib import admin
from .models import Announcement
from django.utils import timezone


class AnnouncementAdmin(admin.ModelAdmin):
    """Admin configuration for Announcement"""

    list_display = (
        "title",
        "author",
        "priority",
        "is_church_wide",
        "is_published",
        "publish_at",
        "expires_at",
    )
    list_filter = ("priority", "is_church_wide", "is_published", "publish_at", "author")
    search_fields = (
        "title",
        "content",
        "author__first_name",
        "author__last_name",
        "author__email",
    )
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("target_groups", "target_members")
    fieldsets = (
        ("Basic Information", {"fields": ("title", "content", "priority")}),
        (
            "Audience Targeting",
            {"fields": ("is_church_wide", "target_groups", "target_members")},
        ),
        ("Scheduling", {"fields": ("publish_at", "expires_at", "is_published")}),
        ("Author Information", {"fields": ("author",), "classes": ("collapse",)}),
        (
            "System Information",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        # Set author if not set
        if not obj.author:
            obj.author = request.user

        # Auto-publish if publish date is in past
        if obj.publish_at and obj.publish_at <= timezone.now():
            obj.is_published = True

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related("author").prefetch_related(
            "target_groups", "target_members"
        )
        return queryset


admin.site.register(Announcement, AnnouncementAdmin)
