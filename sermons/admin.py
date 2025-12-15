from django.contrib import admin
from .models import Sermon


class SermonAdmin(admin.ModelAdmin):
    """Admin configuration for Sermon"""

    list_display = [
        "title",
        "get_preacher_name_display",
        "sermon_date",
        "sermon_type",
        "has_media",
        "created_at",
    ]
    list_filter = ["sermon_type", "sermon_date", "created_at"]
    search_fields = [
        "title",
        "summary",
        "scripture_reference",
        "preacher__first_name",
        "preacher__last_name",
        "guest_preacher_name",
    ]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Basic Information", {"fields": ("title", "sermon_date", "sermon_type")}),
        (
            "Preacher Information",
            {
                "fields": ("preacher", "guest_preacher_name"),
                "description": "Select a registered member or enter a guest preacher name.",
            },
        ),
        ("Content", {"fields": ("scripture_reference", "summary", "full_notes")}),
        (
            "Media Files",
            {
                "fields": (
                    "thumbnail_image",
                    "audio_file",
                    "video_url",
                    "slides_file",
                    "handout_file",
                )
            },
        ),
        ("Series & Tags", {"fields": ("series", "series_part", "tags")}),
        ("Metadata", {"fields": ("duration_minutes", "attendance_count")}),
        (
            "System Information",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_preacher_name_display(self, obj):
        return obj.get_preacher_name()

    get_preacher_name_display.short_description = "Preacher"

    def has_media(self, obj):
        return obj.has_media

    has_media.boolean = True
    has_media.short_description = "Has Media"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related("preacher", "created_by")
        return queryset


admin.site.register(Sermon, SermonAdmin)
