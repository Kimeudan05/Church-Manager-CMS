from django.contrib import admin
from .models import ChurchGroup, Membership, UserRole


class MembershipInline(admin.TabularInline):
    """Inline membership display for groups"""

    model = Membership
    extra = 0
    fields = ["member", "is_primary", "role", "date_joined"]
    readonly_fields = ["date_joined"]


class ChurchGroupAdmin(admin.ModelAdmin):
    """Admin configuration for church group"""

    list_display = ["name", "group_type", "member_count", "leader_count", "created_at"]
    list_filter = ["group_type", "created_at"]
    search_fields = ["name", "description"]
    filter_horizontal = ["leaders"]
    inlines = [MembershipInline]
    readonly_fields = ["member_count", "leader_count"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "group_type", "description")}),
        (
            "Leadership",
            {
                "fields": ("leaders",),
                "description": "Select up to 3 leaders for this group.",
            },
        ),
    )

    def member_count(self, obj):
        return obj.group_members.count()

    member_count.short_description = "Members"

    def leader_count(self, obj):
        return obj.leaders.count()

    leader_count.short_description = "Leaders"


class MembershipAdmin(admin.ModelAdmin):
    """Admin configuration for  Membership"""

    list_display = ["member", "group", "is_primary", "role", "date_joined"]
    list_filter = ["is_primary", "group", "date_joined"]
    search_fields = ["member__username", "member__email", "group__name"]
    raw_id_fields = ["member", "group"]
    readonly_fields = ["date_joined"]

    fieldsets = (
        ("Membership Details", {"fields": ("member", "group", "is_primary", "role")}),
        ("Metadata", {"fields": ("date_joined",), "classes": ("collapse",)}),
    )


class UserRoleAdmin(admin.ModelAdmin):
    """Admin configuration for UserRole"""

    list_display = [
        "user",
        "role_type",
        "can_manage_members",
        "can_manage_events",
        "valid_from",
    ]
    list_filter = ["role_type", "can_manage_members", "can_manage_events"]
    search_fields = [
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    filter_horizontal = ["assigned_groups", "permissions_granted"]

    fieldsets = (
        ("User & Role", {"fields": ("user", "role_type")}),
        (
            "Permissions",
            {
                "fields": (
                    "can_manage_members",
                    "can_manage_events",
                    "can_manage_finances",
                    "can_send_announcements",
                )
            },
        ),
        (
            "Advanced",
            {
                "fields": ("assigned_groups", "permissions_granted"),
                "classes": ("collapse",),
            },
        ),
        ("Validity", {"fields": ("valid_from", "valid_to")}),
    )


# register the models
admin.site.register(ChurchGroup, ChurchGroupAdmin)
admin.site.register(Membership, MembershipAdmin)
admin.site.register(UserRole, UserRoleAdmin)
