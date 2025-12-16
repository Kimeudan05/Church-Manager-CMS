from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Project, Task
from groups.models import ChurchGroup
from accounts.models import CustomUser


class ProjectForm(forms.ModelForm):
    """Form for creating/editing projects"""

    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "project_type",
            "status",
            "responsible_group",
            "project_leader",
            "team_members",
            "start_date",
            "target_end_date",
            "budget_amount",
            "progress_percentage",
            "milestones",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter project title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the project...",
                }
            ),
            "project_type": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "responsible_group": forms.Select(attrs={"class": "form-control"}),
            "project_leader": forms.Select(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "target_end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "budget_amount": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "0.01"}
            ),
            "progress_percentage": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "max": "100"}
            ),
            "milestones": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe milestones (one per line)",
                }
            ),
            "team_members": forms.SelectMultiple(
                attrs={
                    "class": "form-control select2-multiple",
                    "data-placeholder": "Select team members...",
                }
            ),
        }
        help_texts = {
            "progress_percentage": "Current completion percentage (0-100)",
            "milestones": "List major milestones for this project",
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Filter active groups and users
        self.fields["responsible_group"].queryset = ChurchGroup.objects.all()
        self.fields["project_leader"].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by("last_name", "first_name")
        self.fields["team_members"].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by("last_name", "first_name")

        # Set initial dates if new project
        if not self.instance.pk:
            self.fields["start_date"].initial = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        target_end_date = cleaned_data.get("target_end_date")
        budget_amount = cleaned_data.get("budget_amount")

        # Validate dates
        if start_date and target_end_date:
            if start_date > target_end_date:
                raise ValidationError(
                    {"target_end_date": "Target end date must be after start date."}
                )

        # Validate budget
        if budget_amount is not None and budget_amount < 0:
            raise ValidationError({"budget_amount": "Budget cannot be negative."})

        return cleaned_data

    def clean_progress_percentage(self):
        progress = self.cleaned_data.get("progress_percentage")
        if progress < 0 or progress > 100:
            raise ValidationError("Progress must be between 0 and 100.")
        return progress

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()  # Save team_members
        return instance


class TaskForm(forms.ModelForm):
    """Form for creating/editing tasks"""

    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "project",
            "assigned_to",
            "due_date",
            "priority",
            "status",
            "cost",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter task title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe the task...",
                }
            ),
            "project": forms.Select(attrs={"class": "form-control"}),
            "assigned_to": forms.Select(attrs={"class": "form-control"}),
            "due_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "cost": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Filter active users for assignment
        self.fields["assigned_to"].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by("last_name", "first_name")

        # If editing existing task, pre-fill assigned_by
        if self.instance.pk and self.instance.assigned_by:
            self.fields["assigned_by_initial"] = forms.CharField(
                initial=self.instance.assigned_by.get_full_name(),
                widget=forms.TextInput(
                    attrs={"class": "form-control", "readonly": True}
                ),
                required=False,
                label="Assigned By",
            )

        # Set assigned_by to current user if not set
        if self.request and not self.instance.assigned_by:
            self.instance.assigned_by = self.request.user

    def clean_due_date(self):
        due_date = self.cleaned_data.get("due_date")
        if due_date and due_date < timezone.now().date():
            raise ValidationError("Due date cannot be in the past.")
        return due_date

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Auto-complete if status is completed
        if instance.status == "completed" and not instance.completed_at:
            instance.completed_at = timezone.now().date()

        if commit:
            instance.save()
        return instance


class ProjectFilterForm(forms.Form):
    """Form for filtering projects"""

    project_type = forms.ChoiceField(
        choices=[("", "All Types")] + Project.PROJECT_TYPES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    status = forms.ChoiceField(
        choices=[("", "All Statuses")] + Project.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    responsible_group = forms.ModelChoiceField(
        queryset=ChurchGroup.objects.all(),
        required=False,
        empty_label="All Groups",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    start_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "placeholder": "From"}
        ),
    )

    start_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "placeholder": "To"}
        ),
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search projects..."}
        ),
    )


class TaskFilterForm(forms.Form):
    """Form for filtering tasks"""

    priority = forms.ChoiceField(
        choices=[("", "All Priorities")] + Task.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    status = forms.ChoiceField(
        choices=[("", "All Statuses")] + Task.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    assigned_to = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True),
        required=False,
        empty_label="All Users",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    due_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    due_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search tasks..."}
        ),
    )
