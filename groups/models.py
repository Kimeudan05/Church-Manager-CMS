from django.db import models
from django.conf import settings
from django.contrib.auth.models import Permission


class ChurchGroup(models.Model):
    """Groups in the church."""

    GROUP_TYPES = [
        ("men", "Men's Fellowship"),
        ("women", "Women's Fellowship"),
        ("youth", "Youth Group"),
        ("sunday_school", "Sunday School"),
        ("choir", "Choir"),
        ("prayer", "Prayer Group"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=100)
    group_type = models.CharField(max_length=100, choices=GROUP_TYPES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    leaders = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="leading_groups",
        blank=True,
        limit_choices_to={"is_active": True},
    )

    def __str__(self):
        return f"{self.name} ({self.get_group_type_display()})"


class Membership(models.Model):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    group = models.ForeignKey(
        ChurchGroup, on_delete=models.CASCADE, related_name="group_members"
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    is_primary = models.BooleanField(default=False)
    role = models.CharField(max_length=120, blank=True, null=True)

    class Meta:
        unique_together = ("member", "group")
        ordering = ["-is_primary", "date_joined"]

    def save(self, *args, **kwargs):
        if self.is_primary:
            Membership.objects.filter(member=self.member).exclude(pk=self.pk).update(
                is_primary=False
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.username} - {self.group.name} ({'Primary' if self.is_primary else 'Secondary'})"


class UserRole(models.Model):
    ROLE_TYPES = [
        ("super_admin", "Super Admin"),
        ("church_admin", "Church Admin"),
        ("sub_admin", "Sub Admin"),
        ("group_leader", "Group Leader"),
        ("teacher", "Sunday School Teacher"),
        ("member", "Member"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="church_role"
    )
    role_type = models.CharField(max_length=100, choices=ROLE_TYPES, default="member")
    assigned_groups = models.ManyToManyField(
        ChurchGroup, blank=True, related_name="assigned_roles"
    )
    permissions_granted = models.ManyToManyField(Permission, blank=True)

    can_manage_members = models.BooleanField(default=False)
    can_manage_events = models.BooleanField(default=False)
    can_manage_finances = models.BooleanField(default=False)
    can_send_announcements = models.BooleanField(default=False)

    valid_from = models.DateField(auto_now_add=True)
    valid_to = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_type_display()}"
