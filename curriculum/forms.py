from django import forms
from django.utils import timezone

from accounts.models import CustomUser
from .models import Curriculum, Lesson, LessonAttendance
from groups.models import ChurchGroup


class CurriculumForm(forms.ModelForm):
    """Form for creating/updating curriculum"""

    class Meta:
        model = Curriculum
        fields = [
            "title",
            "curriculum_type",
            "description",
            "target_group",
            "start_date",
            "end_date",
            "total_lessons",
            "status",
            "resource_file",
            "external_link",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "e.g. Foundations of Christian Faith"}
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Brief overview of what this curriculum covers",
                }
            ),
            "total_lessons": forms.NumberInput(attrs={"placeholder": "e.g. 12"}),
            "external_link": forms.URLInput(
                attrs={"placeholder": "https://example.com/resource"}
            ),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

        help_texts = {
            "total_lessons": "Total number of lessons in this curriculum",
            "external_link": "Optional link to external resources",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Only show groups the user has access to
        if self.user:
            self.fields["target_group"].queryset = ChurchGroup.objects.all()
        if not self.instance.pk:
            self.fields["status"].initial = "draft"

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        total_lessons = cleaned_data.get("total_lessons")

        if start_date and end_date:
            if end_date < start_date:
                self.add_error("end_date", "End date cannot be before start date")

            if (end_date - start_date).days > 730:
                self.add_error("end_date", "Curriculum duration cannot exceed 2 years")

        if total_lessons and total_lessons <= 0:
            self.add_error("total_lessons", "Must have at least 1 lesson")

        return cleaned_data


class LessonForm(forms.ModelForm):
    """Form for creating/updating lessons"""

    class Meta:
        model = Lesson
        fields = [
            "lesson_number",
            "title",
            "objective",
            "scripture_reference",
            "difficulty",
            "estimated_duration",
            "introduction",
            "teacher_guide",
            "student_materials",
            "activities",
            "discussion_questions",
            "conclusion",
            "scheduled_date",
            "teacher",
            "presentation_file",
            "handout_file",
            "audio_video",
            "additional_files",
        ]

        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. The Birth of Jesus"}),
            "scripture_reference": forms.TextInput(
                attrs={"placeholder": "e.g. Luke 2:1–20"}
            ),
            "estimated_duration": forms.NumberInput(
                attrs={"placeholder": "Minutes (e.g. 60)"}
            ),
            "objective": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "What should students learn from this lesson?",
                }
            ),
            "introduction": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Brief overview or opening illustration",
                }
            ),
            "teacher_guide": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Step-by-step teaching notes for the instructor",
                }
            ),
            "student_materials": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Notes, worksheets, or key points for students",
                }
            ),
            "activities": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Games, group work, or interactive activities",
                }
            ),
            "discussion_questions": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Questions to encourage discussion",
                }
            ),
            "conclusion": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Summary and closing prayer or reflection",
                }
            ),
            "scheduled_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "placeholder": "YYYY-MM-DD",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.curriculum = kwargs.pop("curriculum", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.curriculum:
            # Limit teacher choices to users in the target group
            self.fields["teacher"].queryset = self.curriculum.target_group.leaders.all()

            # Suggest next lesson number
            if not self.instance.pk:
                last_lesson = (
                    Lesson.objects.filter(curriculum=self.curriculum)
                    .order_by("lesson_number")
                    .last()
                )
                self.fields["lesson_number"].initial = (
                    last_lesson.lesson_number + 1 if last_lesson else 1
                )

    def clean(self):
        cleaned_data = super().clean()
        lesson_number = cleaned_data.get("lesson_number")
        curriculum = self.curriculum or self.instance.curriculum

        if lesson_number and curriculum:
            qs = Lesson.objects.filter(
                curriculum=curriculum, lesson_number=lesson_number
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error(
                    "lesson_number",
                    f"Lesson number {lesson_number} already exists in this curriculum",
                )

            if curriculum.total_lessons and lesson_number > curriculum.total_lessons:
                self.add_error(
                    "lesson_number",
                    f"Lesson number cannot exceed total lessons ({curriculum.total_lessons})",
                )

        return cleaned_data


class LessonMarkTaughtForm(forms.ModelForm):
    """Form for marking a lesson as taught"""

    date_taught = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), initial=timezone.now().date
    )
    attendance_count = forms.IntegerField(
        min_value=0, initial=0, help_text="Number of attendees"
    )

    class Meta:
        model = Lesson
        fields = ["date_taught", "teacher", "attendance_count"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.curriculum:
            self.fields["teacher"].queryset = (
                self.instance.curriculum.target_group.leaders.all()
            )


class AttendanceForm(forms.ModelForm):
    """Form for taking attendance for a lesson"""

    member = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        label="Member",
    )

    class Meta:
        model = LessonAttendance
        fields = ["member", "attended", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        self.lesson = kwargs.pop("lesson", None)
        super().__init__(*args, **kwargs)

        if self.lesson:
            group = self.lesson.curriculum.target_group
            # Extract CustomUser instances from Memberships
            user_ids = group.group_members.values_list("member_id", flat=True)
            self.fields["member"].queryset = CustomUser.objects.filter(id__in=user_ids)


class BulkAttendanceForm(forms.Form):
    """Form for bulk attendance marking"""

    lesson = forms.ModelChoiceField(
        queryset=Lesson.objects.all(), widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        self.lesson = kwargs.pop("lesson", None)
        super().__init__(*args, **kwargs)

        if self.lesson:
            self.fields["lesson"].initial = self.lesson
            group = self.lesson.curriculum.target_group

            for membership in group.group_members.all():
                user = membership.member  # ✅ Get the CustomUser
                field_name = f"member_{user.id}"
                self.fields[field_name] = forms.BooleanField(
                    label=user.get_full_name(),  # ✅ Now works
                    required=False,
                    initial=True,
                )
