from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Sermon
from accounts.models import CustomUser


class SermonForm(forms.ModelForm):
    """Form for creating/editing sermons"""

    class Meta:
        model = Sermon
        fields = [
            "title",
            "preacher",
            "guest_speaker_name",
            "sermon_date",
            "sermon_type",
            "scripture_reference",
            "summary",
            "full_notes",
            "audio_file",
            "video_url",
            "slides_file",
            "handout_file",
            "thumbnail_image",
            "tags",
            "duration_minutes",
            "attendance_count",
            "series",
            "series_part",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter sermon title"}
            ),
            "preacher": forms.Select(attrs={"class": "form-control"}),
            "guest_speaker_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter guest preacher name",
                }
            ),
            "sermon_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "sermon_type": forms.Select(attrs={"class": "form-control"}),
            "scripture_reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., John 3:16, Genesis 1:1-5",
                }
            ),
            "summary": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Brief summary of the sermon",
                }
            ),
            "full_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 8,
                    "placeholder": "Full sermon notes or transcript",
                }
            ),
            "audio_file": forms.FileInput(attrs={"class": "form-control"}),
            "video_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://youtube.com/...",
                }
            ),
            "slides_file": forms.FileInput(attrs={"class": "form-control"}),
            "handout_file": forms.FileInput(attrs={"class": "form-control"}),
            "thumbnail_image": forms.FileInput(attrs={"class": "form-control"}),
            "tags": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "love, faith, forgiveness",
                }
            ),
            "duration_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "attendance_count": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "series": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Sermon series name"}
            ),
            "series_part": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "Part number",
                }
            ),
        }
        help_texts = {
            "guest_speaker_name": "Use this only if preacher is not a registered member",
            "scripture_reference": "Separate multiple references with commas",
            "tags": "Separate tags with commas",
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Filter preachers to active members only
        self.fields["preacher"].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by("last_name", "first_name")

        # Make file fields not required
        self.fields["audio_file"].required = False
        self.fields["slides_file"].required = False
        self.fields["handout_file"].required = False
        self.fields["thumbnail_image"].required = False

        # Add dynamic help text
        if self.instance.pk and self.instance.preacher:
            self.fields["preacher"].help_text = (
                f"Currently: {self.instance.get_preacher_name()}"
            )

        # Set initial sermon date to today if new
        if not self.instance.pk:
            self.fields["sermon_date"].initial = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        preacher = cleaned_data.get("preacher")
        guest_speaker_name = cleaned_data.get("guest_speaker_name")
        sermon_date = cleaned_data.get("sermon_date")

        # Validate preacher/guest_preacher logic
        if preacher and guest_speaker_name:
            raise ValidationError(
                "Please use either a registered preacher or a guest speaker, not both."
            )

        if not preacher and not guest_speaker_name:
            raise ValidationError(
                "Please specify either a registered preacher or a guest speaker."
            )

        # Validate sermon date not in future
        if sermon_date and sermon_date > timezone.now().date():
            raise ValidationError(
                {"sermon_date": "Sermon date cannot be in the future."}
            )

        # Validate URL if provided
        video_url = cleaned_data.get("video_url")
        if (
            video_url
            and "youtube.com" not in video_url
            and "youtu.be" not in video_url
            and "vimeo.com" not in video_url
        ):
            self.add_warning(
                "video_url", "Only YouTube and Vimeo URLs are recommended."
            )

        return cleaned_data

    def clean_duration_minutes(self):
        duration = self.cleaned_data.get("duration_minutes")
        if duration is not None and duration < 0:
            raise ValidationError("Duration cannot be negative.")
        return duration

    def clean_attendance_count(self):
        attendance = self.cleaned_data.get("attendance_count")
        if attendance is not None and attendance < 0:
            raise ValidationError("Attendance cannot be negative.")
        return attendance

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.request and hasattr(self.request, "user"):
            if not instance.pk:  # Only for new sermons
                instance.created_by = self.request.user
        if commit:
            instance.save()
        return instance


class SermonFilterForm(forms.Form):
    """Form for filtering sermons"""

    preacher_type = forms.ChoiceField(
        choices=[
            ("", "All Preachers"),
            ("member", "Church Members"),
            ("guest", "Guest Preachers"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    sermon_type = forms.ChoiceField(
        choices=[("", "All Types")] + Sermon.SERMON_TYPES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    has_media = forms.ChoiceField(
        choices=[("", "All Sermons"), ("yes", "With Media"), ("no", "Without Media")],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search by title, preacher, or scripture...",
            }
        ),
    )
    series = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Filter by series..."}
        ),
    )


class SermonSearchForm(forms.Form):
    """Simple search form for sermons"""

    query = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search sermons..."}
        ),
    )
