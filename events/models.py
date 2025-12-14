from django.db import models
from django.conf import settings


class Event(models.Model):
    """Church events (church-wide or group-specific)"""

    EVENT_TYPES = [
        ("service", "Church Service"),
        ("meeting", "Meeting"),
        ("fellowship", "Fellowship"),
        ("outreach", "Outreach"),
        ("training", "Training"),
        ("celebration", "Celebration"),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    location = models.CharField(max_length=200)

    # Audience
    is_church_wide = models.BooleanField(default=False)
    allowed_groups = models.ManyToManyField("groups.ChurchGroup", blank=True)
    allowed_members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)

    # Organization
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organized_events",
    )
    assigned_to = models.ForeignKey(
        "groups.ChurchGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="group_events",
    )

    # Logistics
    capacity = models.IntegerField(null=True, blank=True)
    requires_registration = models.BooleanField(default=False)
    registration_deadline = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_datetime"]

    def __str__(self):
        return (
            f"{self.title} - {self.start_datetime:%b %d, %Y}"
            if self.start_datetime
            else self.title
        )


class EventRegistration(models.Model):
    """Track event registrations"""

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="registrations"
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_registrations",
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("event", "member")

    def __str__(self):
        return f"{self.member.username} for {self.event.title}"
