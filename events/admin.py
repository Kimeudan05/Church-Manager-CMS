from django.contrib import admin
from .models import Event, EventRegistration


class EventRegistrationInline(admin.TabularInline):
    """Inline registration display for events"""

    model = EventRegistration
    extra = 0
    fields = ["member", "attended", "registered_at"]
    readonly_fields = ["registered_at"]
    raw_id_fields = ["member"]


class EventAdmin(admin.ModelAdmin):
    """Admin configuration for Event"""

    list_display = [
        "title",
        "event_type",
        "start_datetime",
        "location",
        "organizer",
        "is_church_wide",
    ]
    list_filter = ["event_type", "is_church_wide", "start_datetime"]
    search_fields = ["title", "description", "location"]
    filter_horizontal = ["allowed_groups", "allowed_members"]
    inlines = [EventRegistrationInline]

    fieldsets = (
        ("Basic Information", {"fields": ("title", "description", "event_type")}),
        ("Time & Location", {"fields": ("start_datetime", "end_datetime", "location")}),
        (
            "Audience",
            {
                "fields": (
                    "is_church_wide",
                    "assigned_to",
                    "allowed_groups",
                    "allowed_members",
                )
            },
        ),
        ("Organization", {"fields": ("organizer", "created_by")}),
        (
            "Logistics",
            {"fields": ("capacity", "requires_registration", "registration_deadline")},
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class EventRegistrationAdmin(admin.ModelAdmin):
    """Admin configuration for EventRegistration"""

    list_display = ["event", "member", "attended", "registered_at"]
    list_filter = ["attended", "registered_at", "event"]
    search_fields = ["member__username", "member__email", "event__title"]
    raw_id_fields = ["event", "member"]
    readonly_fields = ["registered_at"]

    fieldsets = (
        ("Registration Details", {"fields": ("event", "member", "attended", "notes")}),
        ("Metadata", {"fields": ("registered_at",), "classes": ("collapse",)}),
    )


admin.site.register(Event, EventAdmin)
admin.site.register(EventRegistration, EventRegistrationAdmin)
