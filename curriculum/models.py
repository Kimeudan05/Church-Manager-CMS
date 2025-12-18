from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from groups.models import ChurchGroup


class Curriculum(models.Model):
    """Teaching curriculum (mainly for Sunday school)"""

    CURRICULUM_CHOICES = [
        ("sunday_school", "Sunday School"),
        ("bible_study", "Bible Study"),
        ("discipleship", "Discipleship"),
        ("training", "Training"),
        ("new_members", "New Members Class"),
        ("leadership", "Leadership Training"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=100)
    curriculum_type = models.CharField(max_length=100, choices=CURRICULUM_CHOICES)
    description = models.TextField()
    target_group = models.ForeignKey(
        ChurchGroup,
        on_delete=models.CASCADE,
        related_name="curriculums",
        help_text="Group this curriculum is designed for",
    )

    # duration
    start_date = models.DateField()
    end_date = models.DateField()
    total_lessons = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Total number of lessons in this curriculum",
    )

    # status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # resources
    resource_file = models.FileField(
        upload_to="curriculum/resources/%Y/%m/",
        null=True,
        blank=True,
        help_text="Main curriculum file (PDF, Word, etc.)",
    )
    external_link = models.URLField(blank=True, help_text="Link to external resource")

    # metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_curriculums",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_curriculums",
        help_text="User who approved this curriculum",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "title"]
        verbose_name_plural = "Curricula"
        indexes = [
            models.Index(fields=["status", "start_date"]),
            models.Index(fields=["curriculum_type", "target_group"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.target_group.name}"

    @property
    def duration_weeks(self):
        """Calculate duration in weeks"""
        from django.utils import timezone
        import math

        if self.start_date and self.end_date:
            days = (self.end_date - self.start_date).days
            return math.ceil(days / 7) if days > 0 else 1
        return 0

    @property
    def progress_percentage(self):
        """Calculate completion percentage based on lessons taught"""
        total_lessons = self.total_lessons
        if total_lessons > 0:
            completed = self.lessons.filter(date_taught__isnull=False).count()
            return int((completed / total_lessons) * 100)
        return 0

    @property
    def is_active(self):
        """Check if curriculum is currently active"""
        from django.utils import timezone

        today = timezone.now().date()
        return self.status == "active" and self.start_date <= today <= self.end_date

    def save(self, *args, **kwargs):
        # Auto-update status based on dates
        from django.utils import timezone

        today = timezone.now().date()

        if self.start_date and self.end_date:
            if today > self.end_date and self.status == "active":
                self.status = "completed"
            elif self.start_date <= today <= self.end_date and self.status == "draft":
                self.status = "active"

        super().save(*args, **kwargs)


class Lesson(models.Model):
    """Individual lessons within a curriculum"""

    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    curriculum = models.ForeignKey(
        Curriculum, on_delete=models.CASCADE, related_name="lessons"
    )

    lesson_number = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Lesson number in sequence"
    )
    title = models.CharField(max_length=100)
    objective = models.TextField(help_text="Learning objective for this lesson")
    scripture_reference = models.CharField(
        max_length=100, help_text="Bible reference (e.g., John 3:16)"
    )

    # lesson details
    difficulty = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default="beginner"
    )
    estimated_duration = models.IntegerField(
        default=60, help_text="Estimated duration in minutes"
    )

    # content sections
    introduction = models.TextField(blank=True, help_text="Lesson introduction")
    teacher_guide = models.TextField(blank=True, help_text="Teacher's guide")
    student_materials = models.TextField(blank=True, help_text="Student materials")
    activities = models.TextField(blank=True, help_text="Classroom activities")
    discussion_questions = models.TextField(
        blank=True, help_text="Discussion questions"
    )
    conclusion = models.TextField(blank=True, help_text="Lesson conclusion")

    # files
    presentation_file = models.FileField(
        upload_to="lessons/presentations/%Y/%m/",
        null=True,
        blank=True,
        help_text="Presentation slides (PPT, PDF)",
    )
    handout_file = models.FileField(
        upload_to="lessons/handouts/%Y/%m/",
        null=True,
        blank=True,
        help_text="Printable handouts",
    )
    audio_video = models.FileField(
        upload_to="lessons/media/%Y/%m/",
        null=True,
        blank=True,
        help_text="Audio or video lesson",
    )
    additional_files = models.FileField(
        upload_to="lessons/additional/%Y/%m/",
        null=True,
        blank=True,
        help_text="Additional resources",
    )

    # scheduling
    date_taught = models.DateField(null=True, blank=True)
    scheduled_date = models.DateField(null=True, blank=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="taught_lessons",
    )

    # tracking
    attendance_count = models.IntegerField(
        default=0, validators=[MinValueValidator(0)], help_text="Number of attendees"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["curriculum", "lesson_number"]
        unique_together = ("curriculum", "lesson_number")
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"
        indexes = [
            models.Index(fields=["curriculum", "date_taught"]),
            models.Index(fields=["teacher", "date_taught"]),
        ]

    def __str__(self):
        return f"Lesson {self.lesson_number}: {self.title}"

    @property
    def is_taught(self):
        """Check if lesson has been taught"""
        return self.date_taught is not None

    @property
    def is_upcoming(self):
        """Check if lesson is scheduled for future"""
        from django.utils import timezone

        today = timezone.now().date()
        return self.scheduled_date and self.scheduled_date > today

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # first save the lesson

        # Optionally, update curriculum status based on lessons taught
        curriculum = self.curriculum
        if curriculum.total_lessons > 0:
            completed_count = curriculum.lessons.filter(
                date_taught__isnull=False
            ).count()
            if completed_count >= curriculum.total_lessons:
                curriculum.status = "completed"
                curriculum.save(update_fields=["status"])


class LessonAttendance(models.Model):
    """Track attendance for each lesson"""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="attendances"
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_attendances",
    )
    attended = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Any observations")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recorded_attendances",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("lesson", "member")
        verbose_name = "Lesson Attendance"
        verbose_name_plural = "Lesson Attendances"

    def __str__(self):
        return f"{self.member} - {self.lesson}"


class CurriculumProgress(models.Model):
    """Track member progress through a curriculum"""

    curriculum = models.ForeignKey(
        Curriculum, on_delete=models.CASCADE, related_name="progress_records"
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="curriculum_progress",
    )
    current_lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="progress_current",
    )
    completed_lessons = models.ManyToManyField(
        Lesson, blank=True, related_name="progress_completed"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("curriculum", "member")
        verbose_name = "Curriculum Progress"
        verbose_name_plural = "Curriculum Progress Records"

    def __str__(self):
        return f"{self.member} - {self.curriculum}"

    @property
    def completion_percentage(self):
        total = self.curriculum.total_lessons
        if total > 0:
            completed = self.completed_lessons.count()
            return int((completed / total) * 100)
        return 0
