from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from groups.models import UserRole
from .forms import CustomUserCreationForm, CustomUserChangeForm


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = [
        "username",
        "email",
        "phone",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
    ]
    list_filter = ["is_staff", "is_superuser", "is_active", "groups"]
    search_fields = ["username", "email", "phone", "first_name", "last_name"]
    readonly_fields = ("member_since",)  # <--- Make member_since read-only

    fieldsets = (
        (None, {"fields": ("username",)}),
        (
            "Personal info",
            {
                "fields": (
                    "email",
                    "phone",
                    "first_name",
                    "last_name",
                    "date_of_birth",
                    "profile_picture",
                )
            },
        ),
        (
            "Church Info",
            {
                "fields": (
                    "status",
                    "baptism_date",
                    "member_since",
                    "occupation",
                    "marital_status",
                )
            },
        ),
        (
            "Emergency Contact",
            {"fields": ("emergency_contact", "emergency_contact_phone")},
        ),
        ("Family", {"fields": ("parents", "spouse")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "is_active",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "phone",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


class UserRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "role_type", "valid_from", "valid_to"]
    list_filter = ("role_type", "can_manage_members", "can_manage_events")
    filter_horizontal = ("assigned_groups", "permissions_granted")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserRole, UserRoleAdmin)
