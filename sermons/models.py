from django.db import models
from accounts.models import CustomUser
from django.core.validators import MinValueValidator
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class Sermon(models.Model):
    """Past Sermons with attachments"""

    SERMON_TYPES = [
        ("sunday", "Sunday Service"),
        ("midweek", "Midweek Service"),
        ("special", "Special Service"),
        ("seminar", "Seminar/Teaching"),
        ("conference", "Conference"),
    ]

    title = models.CharField(max_length=200, help_text="Title of the sermon")
    preacher = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sermons_preached",
        help_text="Select a registered church member",
    )
    guest_speaker_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="name of the guest speaker (If not a registered member)",
    )
    sermon_date = models.DateField()
    sermon_type = models.CharField(
        choices=SERMON_TYPES, max_length=20, default="sunday"
    )

    # Scripture references
    scripture_reference = models.TextField(
        blank=True, null=True, help_text="eg .. John 3:16, Genesis 1-1-5, Psalm 23"
    )

    # Content
    summary = models.TextField(
        blank=True, help_text="Brief summary of the sermon (for display)"
    )
    full_notes = models.TextField(
        blank=True, help_text="Full sermon notes or transcript"
    )
    audio_file = models.FileField(
        upload_to="sermons/audio/",
        null=True,
        blank=True,
        help_text="Upload audio file (MP3, WAV, etc.)",
    )
    video_url = models.URLField(
        blank=True, help_text="Link to video (YouTube, Vimeo, etc.)"
    )
    slides_file = models.FileField(
        upload_to="sermons/slides/",
        null=True,
        blank=True,
        help_text="Upload presentation slides (PDF, PPT, etc.)",
    )
    handout_file = models.FileField(
        upload_to="sermons/handouts/",
        null=True,
        blank=True,
        help_text="Upload handout (PDF, Word, etc.)",
    )
    thumbnail_image = models.ImageField(
        upload_to="sermons/thumbnails/%Y/%m/",
        null=True,
        blank=True,
        help_text="Thumbnail image for the sermon",
    )

    # Metadata
    tags = models.CharField(
        max_length=100,
        blank=True,
        help_text="Comma-separated tags (e.g., love, forgiveness, faith)",
    )
    duration_minutes = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Duration in minutes",
    )
    attendance_count = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Number of people in attendance",
    )

    # Series information
    series = models.CharField(
        max_length=100, blank=True, help_text="Sermon series name (if part of a series)"
    )
    series_part = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Part number in the series",
    )

    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sermons_created",
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sermon_date"]
        verbose_name = "Sermon"
        verbose_name_plural = "Sermons"
        permissions = [
            ("can_manage_sermons", "Can manage sermons"),
            ("can_upload_sermons", "Can upload sermons"),
        ]

    def __str__(self):
        return f"{self.title} - {self.sermon_date.strftime('%b %d, %Y')}"

    def clean(self):
        super().clean()

        # prevent both preacher and guest_speaker_name
        if self.preacher and self.guest_speaker_name:
            raise ValidationError(
                {
                    "preacher": _(
                        "Please use either a registered preacher or a guest speaker, not both."
                    ),
                    "guest_speaker_name": _(
                        "Please use either a registered preacher or a guest speaker, not both."
                    ),
                }
            )

        # Require atleast one preacher
        if not self.preacher and not self.guest_speaker_name:
            raise ValidationError(_, ("Please specify a preacher or guest speaker"))

        # validate sermon date not in future
        from django.utils import timezone

        if self.sermon_date > timezone.now().date():
            raise ValidationError(
                {"sermon_date": _("Sermons date cannot be in the future")}
            )

    def save(self, *args, **kwargs):
        self.clean
        super().save(*args, **kwargs)

    def get_preacher_name(self):
        """Get preacher name, handling both registered users and guests"""
        if self.preacher:
            return self.preacher.get_full_name() or self.preacher.username
        return self.guest_speaker_name or "Guest Speaker"

    def get_absolute_url(self):
        return reverse("sermon:detail", kwargs={"pk": self.pk})

    @property
    def formatted_scripture(self):
        """Format scripture reference for display"""
        if self.scripture_reference:
            return self.scripture_reference
        return "Not specified"

    @property
    def has_media(self):
        """Check if sermon has any media"""
        return any(
            [self.audio_file, self.video_url, self.handout_file, self.thumbnail_image]
        )

    def get_media_count(self):
        """Count of available media files"""
        return sum(
            [
                1 if self.audio_file else 0,
                1 if self.video_url else 0,
                1 if self.slides_file else 0,
                1 if self.handout_file else 0,
            ]
        )

    @property
    def is_recent(self):
        """Check if sermon is from last 30 days"""
        from datetime import timedelta
        from django.utils import timezone

        return self.sermon_date >= (timezone.now().date() - timedelta(days=30))

    @property
    def tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(",")]
        return []
