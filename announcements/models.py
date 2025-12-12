from django.db import models
from django.conf import settings
from django.utils import timezone
from groups.models import ChurchGroup


class Announcement(models.Model):
    """Church Announcements"""

    PRIORITY_LEVELS = [
        ("urgent", "Urgent - Immediate Attention"),
        ("high", "High - Important"),
        ("normal", "Normal"),
        ("low", "Low - Informational"),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(
        max_length=10, choices=PRIORITY_LEVELS, default="normal"
    )

    # target audience
    is_church_wide = models.BooleanField(default=False)
    target_groups = models.ManyToManyField(
        ChurchGroup, blank=True, related_name="announcements"
    )
    target_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="personal_announcements"
    )

    # scheduling
    publish_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="authored_announcements",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # status
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("-publish_at",)

    def __str__(self):
        if self.publish_at:
            return f"{self.title} ({self.publish_at:%b %d})"
        return self.title
