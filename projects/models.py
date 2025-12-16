from django.db import models
from groups.models import ChurchGroup
from accounts.models import CustomUser
from django.core.validators import MinValueValidator, MaxValueValidator


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
        CustomUser, on_delete=models.CASCADE, related_name="led_projects"
    )
    team_members = models.ManyToManyField(
        CustomUser, related_name="assigned_projects", blank=True
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

    def can_edit_project(self, user):
        # Staff can edit any project
        if user.is_staff:
            return True

        # Project leader can edit
        if self.project_leader == user:
            return True

        # Group leaders of the responsible group can edit
        if hasattr(user, "church_role"):
            return self.responsible_group in user.church_role.assigned_groups.all()

        return False

    def update_actual_spent(self):
        """Calculate and update the total actual spent amount for the project."""
        total_spent = (
            self.tasks.aggregate(total_spent=models.Sum("cost"))["total_spent"] or 0.00
        )
        self.actual_spent = total_spent
        self.save()


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
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
        null=True,
        blank=True,
    )
    assigned_by = models.ForeignKey(
        CustomUser,
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
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text="Cost for this task"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "priority"]

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
