from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Event, EventRegistration
from groups.models import ChurchGroup, UserRole
from accounts.models import CustomUser


class EventForm(forms.ModelForm):
    """Form for creating/editing events"""

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "event_type",
            "start_datetime",
            "end_datetime",
            "location",
            "is_church_wide",
            "allowed_groups",
            "allowed_members",
            "organizer",
            "assigned_to",
            "capacity",
            "requires_registration",
            "registration_deadline",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Event Title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Event Description ...",
                }
            ),
            "event_type": forms.Select(attrs={"class": "form-control"}),
            "start_datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Event Location"}
            ),
            "is_church_wide": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "allowed_groups": forms.SelectMultiple(
                attrs={"class": "form-control", "size": 5}
            ),
            "allowed_members": forms.SelectMultiple(
                attrs={"class": "form-control", "size": 5}
            ),
            "organizer": forms.Select(attrs={"class": "form-control"}),
            "assigned_to": forms.Select(attrs={"class": "form-control"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control"}),
            "requires_registration": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "registration_deadline": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Set initial values
        if not self.instance.pk:
            if self.request and hasattr(self.request, "user"):
                self.fields["organizer"].initial = self.request.user

        # Filter groups and members based on user permissions
        if self.request and hasattr(self.request, "user"):
            user = self.request.user

            # Determine which ChurchGroups user can assign
            if user.is_staff or user.is_superuser:
                # Admins can assign to all ChurchGroups
                allowed_groups_queryset = ChurchGroup.objects.all().order_by("name")
                assigned_to_queryset = ChurchGroup.objects.all().order_by("name")
            elif hasattr(user, "church_role"):
                church_role = user.church_role

                if church_role.role_type in ["super_admin", "church_admin"]:
                    # Church admins can assign to all ChurchGroups
                    allowed_groups_queryset = ChurchGroup.objects.all().order_by("name")
                    assigned_to_queryset = ChurchGroup.objects.all().order_by("name")
                elif church_role.role_type == "group_leader":
                    # Group leaders can only assign to their groups
                    allowed_groups_queryset = user.leading_groups.all().order_by("name")
                    assigned_to_queryset = user.leading_groups.all().order_by("name")
                else:
                    # Regular users can't assign groups
                    allowed_groups_queryset = ChurchGroup.objects.none()
                    assigned_to_queryset = ChurchGroup.objects.none()
            else:
                allowed_groups_queryset = ChurchGroup.objects.none()
                assigned_to_queryset = ChurchGroup.objects.none()

            # For existing events, include the already selected groups
            if self.instance.pk:
                existing_allowed_groups = self.instance.allowed_groups.all()
                if existing_allowed_groups:
                    allowed_groups_queryset = (
                        allowed_groups_queryset | existing_allowed_groups
                    ).distinct()

                if self.instance.assigned_to:
                    assigned_to_queryset = (
                        assigned_to_queryset
                        | ChurchGroup.objects.filter(id=self.instance.assigned_to.id)
                    ).distinct()

        else:
            allowed_groups_queryset = ChurchGroup.objects.all().order_by("name")
            assigned_to_queryset = ChurchGroup.objects.all().order_by("name")

        self.fields["allowed_groups"].queryset = allowed_groups_queryset
        self.fields["assigned_to"].queryset = assigned_to_queryset

        # Filter members
        self.fields["allowed_members"].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by("last_name", "first_name")

        self.fields["organizer"].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by("last_name", "first_name")

        # Make fields conditional
        self.fields["registration_deadline"].required = False
        self.fields["capacity"].required = False
        self.fields["allowed_groups"].required = False
        self.fields["allowed_members"].required = False
        self.fields["assigned_to"].required = False

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        registration_deadline = cleaned_data.get("registration_deadline")

        # Check that end datetime is after start datetime
        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise ValidationError("End date/time must be after start date/time.")

        # Check that registration deadline is before event start
        if (
            registration_deadline
            and start_datetime
            and registration_deadline >= start_datetime
        ):
            raise ValidationError(
                "Registration deadline must be before the event start time."
            )

        # Check that church-wide events don't have assigned groups/members
        if cleaned_data.get("is_church_wide"):
            if cleaned_data.get("assigned_to"):
                raise ValidationError(
                    "Church-wide events cannot be assigned to a specific group."
                )
            if cleaned_data.get("allowed_groups"):
                raise ValidationError(
                    "Church-wide events cannot have allowed groups (they're for everyone)."
                )
            if cleaned_data.get("allowed_members"):
                raise ValidationError(
                    "Church-wide events cannot have allowed members (they're for everyone)."
                )

        return cleaned_data

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")
        if capacity is not None and capacity <= 0:
            raise ValidationError("Capacity must be a positive number.")
        return capacity


class EventRegistrationForm(forms.ModelForm):
    """Form for event registration"""

    class Meta:
        model = EventRegistration
        fields = ["event", "member", "notes"]
        widgets = {
            "event": forms.Select(attrs={"class": "form-control"}),
            "member": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)

        if event:
            self.fields["event"].initial = event
            self.fields["event"].widget = forms.HiddenInput()

        if self.request and hasattr(self.request, "user"):
            self.fields["member"].initial = self.request.user
            self.fields["member"].widget = forms.HiddenInput()

        # Filter active members
        self.fields["member"].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by("last_name", "first_name")

    def clean(self):
        """
        Form-level validation and normalization.

        Validates event dates, registration rules,
        and normalizes group-related fields for church-wide events.
        """

        cleaned_data = super().clean()

        # Extract commonly used fields
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        registration_deadline = cleaned_data.get("registration_deadline")
        is_church_wide = cleaned_data.get("is_church_wide")
        requires_registration = cleaned_data.get("requires_registration")

        # Validate event date order
        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise ValidationError("End date/time must be after start date/time.")

        # Validate registration deadline timing
        if (
            registration_deadline
            and start_datetime
            and registration_deadline >= start_datetime
        ):
            raise ValidationError(
                "Registration deadline must be before the event start time."
            )

        # Normalize data for church-wide events
        if is_church_wide:
            cleaned_data["assigned_to"] = None
            cleaned_data["allowed_groups"] = []
            cleaned_data["allowed_members"] = []

        # Validate registration requirements
        if requires_registration and not registration_deadline:
            raise ValidationError(
                "Registration deadline is required when registration is enabled."
            )

        return cleaned_data


class EventFilterForm(forms.Form):
    """Form for filtering events"""

    event_type = forms.ChoiceField(
        choices=[("", "All Types")] + Event.EVENT_TYPES,
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
    is_church_wide = forms.ChoiceField(
        choices=[("", "All Events"), ("yes", "Church-wide"), ("no", "Group-specific")],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    group = forms.ModelChoiceField(
        queryset=ChurchGroup.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
