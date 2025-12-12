from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Sermon(models.Model):
    """Past Sermons with attachments"""

    SERMON_TYPES = [
        ("sunday", "Sunday Service"),
        ("midweek", "Midweek Service"),
        ("special", "Special Service"),
        ("seminar", "Seminar/Teaching"),
    ]

    title = models.CharField(max_length=100)
    preacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sermons_preached",
    )
    sermon_date = models.DateField()
    sermon_type = models.CharField(
        choices=SERMON_TYPES, max_length=20, default="sunday"
    )

    # Scripture references
    scripture_reference = models.TextField(blank=True)

    # Content
    summary = models.TextField(blank=True)
    full_notes = models.TextField(blank=True)
    audio_file = models.FileField(upload_to="sermons/audio/", null=True, blank=True)
    video_url = models.URLField(blank=True)
    slides_file = models.FileField(upload_to="sermons/slides/", null=True, blank=True)
    handout_file = models.FileField(
        upload_to="sermons/handouts/", null=True, blank=True
    )

    # Metadata
    tags = models.CharField(max_length=100, blank=True)
    duration_minutes = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    attendance_count = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sermon_date"]

    def __str__(self):
        return f"{self.title} - {self.sermon_date.strftime('%b %d, %Y')}"

    def scripture_reference(self):
        if self.start_verse and self.end_verse:
            return (
                f"{self.bible_book} {self.chapter}:{self.start_verse}-{self.end_verse}"
            )
        return f"{self.bible_book} {self.chapter}"
