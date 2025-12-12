from django.db import models
from django.conf import settings
from groups.models import ChurchGroup


class Curriculum(models.Model):
    """Teaching curriculum (mainly for Sunday school)"""

    CURRICULUM_CHOICES = [
        ("sunday_school", "Sunday School"),
        ("bible_study", "Bible Study"),
        ("discipleship", "Discipleship"),
        ("training", "Training"),
    ]

    title = models.CharField(max_length=100)
    curriculum_type = models.CharField(max_length=100, choices=CURRICULUM_CHOICES)
    description = models.TextField()
    target_group = models.ForeignKey(
        ChurchGroup, on_delete=models.CASCADE, related_name="curriculums"
    )

    # duration
    start_date = models.DateField()
    end_date = models.DateField()
    total_lessons = models.IntegerField(default=1)

    # resources
    resource_file = models.FileField(
        upload_to="curriculum/resources/%Y/%m/", null=True, blank=True
    )
    external_link = models.URLField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.target_group.name}"


class Lesson(models.Model):
    """Individual lessons within a curriculum"""

    curriculum = models.ForeignKey(
        Curriculum, on_delete=models.CASCADE, related_name="lessons"
    )

    lesson_number = models.IntegerField()
    title = models.CharField(max_length=100)
    objective = models.TextField()
    scripture_reference = models.CharField(max_length=100)

    # content
    teacher_guide = models.TextField(blank=True)
    student_materials = models.TextField(blank=True)
    activities = models.TextField(blank=True)
    discussion_questions = models.TextField(blank=True)

    # files
    presentation_file = models.FileField(
        upload_to="lessons/presentations/%Y/%m/", null=True, blank=True
    )
    handout_file = models.FileField(
        upload_to="lessons/handouts/%Y/%m/", null=True, blank=True
    )
    audio_video = models.FileField(
        upload_to="lessons/media/%Y/%m/", null=True, blank=True
    )

    date_taught = models.DateField()
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["curriculum", "lesson_number"]
        unique_together = ("curriculum", "lesson_number")

    def __str__(self):
        return f"Lesson {self.lesson_number} : {self.title}"
