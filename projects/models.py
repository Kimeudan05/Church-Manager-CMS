from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class ChurchGroup(models.Model):
    """Groups in the church (Men, Women, Youth, etc.)"""

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

    def __str__(self):
        return f"{self.name} ({self.get_group_type_display()})"


class Project(models.Model):
    """Group Projects (Outreach, Service, Fundraising, etc.)"""

    PROJECT_TYPES = [
        ("outreach", "Outreach/Mission"),
        ("service", "Community Service"),
        ("fundraising", "Fundraising"),
        ("building", "Building/Repair"),
        ("social", "Social Event"),
    ]

    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    project_type = models.CharField(max_length=100, choices=PROJECT_TYPES)
    status = models.CharField(
        max_length=100, choices=STATUS_CHOICES, default="planning"
    )

    # Organization
    responsible_group = models.ForeignKey(
        ChurchGroup, on_delete=models.CASCADE, related_name="projects"
    )
    project_leader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="led_projects"
    )
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="assigned_projects", blank=True
    )

    # Timeline
    start_date = models.DateField(null=True, blank=True)
    target_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)

    # Budget
    budget_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    actual_spent = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Progress
    progress_percentage = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)], default=0
    )
    milestones = models.TextField(
        blank=True, help_text="JSON or text describing milestones"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "title"]

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


class Task(models.Model):
    """Task within a Project"""

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("blocked", "Blocked"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=100)
    description = models.TextField()

    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
        null=True,
        blank=True,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_tasks",
        null=True,
        blank=True,
    )

    # Timeline
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateField(null=True, blank=True)

    # Status & priority
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "priority"]

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
