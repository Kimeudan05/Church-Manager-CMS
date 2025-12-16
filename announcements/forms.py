from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Announcement
from groups.models import ChurchGroup
from accounts.models import CustomUser


class AnnouncementForm(forms.ModelForm):
    """Form for creating/editing announcements"""

    class Meta:
        model = Announcement
        fields = [
            "title",
            "content",
            "priority",
            "is_church_wide",
            "target_groups",
            "target_members",
            "publish_at",
            "expires_at",
            "is_published",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter announcement title",
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Enter announcement content...",
                }
            ),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "is_church_wide": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "publish_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "expires_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "target_groups": forms.SelectMultiple(
                attrs={
                    "class": "form-control select2-multiple",
                    "data-placeholder": "Select target groups...",
                }
            ),
            "target_members": forms.SelectMultiple(
                attrs={
                    "class": "form-control select2-multiple",
                    "data-placeholder": "Select target members...",
                }
            ),
        }
        help_texts = {
            "is_church_wide": "If checked, this announcement will be shown to all church members",
            "target_groups": "Select specific groups to target (optional if church-wide)",
            "target_members": "Select specific members to target (optional)",
            "publish_at": "Schedule when this announcement should become visible",
            "expires_at": "Set when this announcement should expire (optional)",
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Filter active groups and users
        self.fields["target_groups"].queryset = ChurchGroup.objects.all().order_by(
            "name"
        )
        self.fields["target_members"].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by("last_name", "first_name")

        # Set initial publish date to now if new announcement
        if not self.instance.pk:
            now = timezone.now()
            # Round to nearest 5 minutes for better UX
            minute = now.minute - (now.minute % 5)
            rounded_time = now.replace(minute=minute, second=0, microsecond=0)
            self.fields["publish_at"].initial = rounded_time

        # Dynamic help text based on user role
        if self.request and self.request.user.is_authenticated:
            if hasattr(self.request.user, "church_role"):
                if self.request.user.church_role.role_type in ["member"]:
                    self.fields["is_published"].help_text = (
                        "Note: Your announcement may need admin approval"
                    )

        # Add CSS classes for styling
        self.fields["title"].widget.attrs.update({"class": "form-control-lg"})
        self.fields["content"].widget.attrs.update(
            {"class": "form-control announcement-content"}
        )

    def clean(self):
        cleaned_data = super().clean()
        publish_at = cleaned_data.get("publish_at")
        expires_at = cleaned_data.get("expires_at")
        is_church_wide = cleaned_data.get("is_church_wide")
        target_groups = cleaned_data.get("target_groups")
        target_members = cleaned_data.get("target_members")

        # Validate dates
        if publish_at and expires_at:
            if publish_at >= expires_at:
                raise ValidationError(
                    {"expires_at": "Expiry date must be after publish date."}
                )

        # Validate that expired announcements aren't published
        if expires_at and expires_at < timezone.now():
            if cleaned_data.get("is_published"):
                raise ValidationError(
                    {
                        "is_published": "Cannot publish an announcement that has already expired."
                    }
                )

        # Validate targeting logic
        if not is_church_wide and not target_groups and not target_members:
            raise ValidationError(
                "Please select at least one target: either 'Church Wide', specific groups, or specific members."
            )

        return cleaned_data

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if len(title) < 5:
            raise ValidationError("Title must be at least 5 characters long.")
        if len(title) > 200:
            raise ValidationError("Title cannot exceed 200 characters.")
        return title

    def clean_content(self):
        content = self.cleaned_data.get("content")
        if len(content) < 10:
            raise ValidationError("Content must be at least 10 characters long.")
        return content

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set author if not set
        if self.request and not instance.author:
            instance.author = self.request.user

        if commit:
            instance.save()
            self.save_m2m()  # Save ManyToMany fields

        return instance


class AnnouncementFilterForm(forms.Form):
    """Form for filtering announcements"""

    PRIORITY_CHOICES = [
        ("", "All Priorities"),
        ("urgent", "Urgent"),
        ("high", "High"),
        ("normal", "Normal"),
        ("low", "Low"),
    ]

    STATUS_CHOICES = [
        ("", "All Statuses"),
        ("published", "Published"),
        ("scheduled", "Scheduled"),
        ("expired", "Expired"),
        ("draft", "Draft"),
    ]

    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    is_church_wide = forms.ChoiceField(
        choices=[("", "All"), ("yes", "Church Wide"), ("no", "Targeted")],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "placeholder": "From date"}
        ),
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "placeholder": "To date"}
        ),
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search announcements..."}
        ),
    )

    author = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True),
        required=False,
        empty_label="All Authors",
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class AnnouncementQuickCreateForm(forms.ModelForm):
    """Simplified form for quick announcements"""

    class Meta:
        model = Announcement
        fields = ["title", "content", "priority", "is_church_wide"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Quick announcement title",
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Brief announcement...",
                }
            ),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "is_church_wide": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Set defaults for quick form
        self.fields["priority"].initial = "normal"
        self.fields["is_church_wide"].initial = True
        self.fields["is_church_wide"].label = "Church Wide"

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Auto-set fields for quick announcements
        if self.request:
            instance.author = self.request.user
            instance.publish_at = timezone.now()
            instance.is_published = True

        if commit:
            instance.save()

        return instance
