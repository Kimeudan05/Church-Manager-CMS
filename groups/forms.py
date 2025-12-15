from django import forms
from django.core.exceptions import ValidationError

from accounts.models import CustomUser
from .models import ChurchGroup, Membership, UserRole
from django.conf import settings


class ChurchGroupForm(forms.ModelForm):
    """Form for creating/editing church groups"""

    class Meta:
        model = ChurchGroup
        fields = ["name", "group_type", "description", "leaders"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter group name..."}
            ),
            "group_type": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter group description...",
                }
            ),
            "leaders": forms.SelectMultiple(
                attrs={"class": "form-control", "size": 5, "multiple": True}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # filter users to only active members

        self.fields["leaders"].queryset = CustomUser.objects.filter(
            is_active=True, status__in=["active", "visitor"]
        ).order_by("last_name", "first_name")

    def clean_leaders(self):
        leaders = self.cleaned_data.get("leaders")
        # enforce max 3 leaders per group
        if leaders and leaders.count() > 3:
            raise ValidationError("Group can have at most 3 leaders")
        return leaders


class AddMembershipForm(forms.ModelForm):
    """Form for adding a member to a group"""

    class Meta:
        model = Membership
        fields = ["member", "group", "is_primary", "role"]
        widgets = {
            "member": forms.Select(attrs={"class": "form-control"}),
            "group": forms.HiddenInput(),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "role": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Role in group ... (Chairman, Treasurer, Secretary, Member ..)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        group = kwargs.pop("group", None)
        super().__init__(*args, **kwargs)

        if group:
            # Show only active users not already in this group
            existing_members = Membership.objects.filter(group=group).values_list(
                "member", flat=True
            )
            self.fields["member"].queryset = (
                CustomUser.objects.filter(
                    is_active=True, status__in=["active", "visitor"]
                )
                .exclude(id__in=existing_members)
                .order_by("last_name", "first_name")
            )
            self.fields["group"].initial = group

    def clean(self):
        cleaned_data = super().clean()
        member = cleaned_data.get("member")
        group = cleaned_data.get("group")

        if member and group:
            # check if already in this group
            if Membership.objects.filter(member=member, group=group).exists():
                raise ValidationError(
                    f"{member.get_full_name()} is already in {group.name}."
                )

            # max 3 groups per member
            if Membership.objects.filter(member=member).count() >= 3:
                raise ValidationError(
                    f"{member.get_full_name()} already belongs to 3 groups."
                )

        return cleaned_data


class UpdateMembershipForm(forms.ModelForm):
    """Form for updating membership (member not editable)"""

    class Meta:
        model = Membership
        fields = ["member", "group", "is_primary", "role"]
        widgets = {
            "member": forms.TextInput(
                attrs={"class": "form-control", "readonly": "readonly"}
            ),
            "group": forms.HiddenInput(),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "role": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Role in group ... (Chairman, Treasurer, Secretary, Member ..)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # make member field read-only (display current member)
        self.fields["member"].disabled = True
        self.fields["member"].initial = self.instance.member.get_full_name()


class UserRoleForm(forms.ModelForm):
    """Form for managing user roles"""

    class Meta:
        model = UserRole
        fields = [
            "user",
            "role_type",
            "assigned_groups",
            "permissions_granted",
            "can_manage_members",
            "can_manage_events",
            "can_manage_finances",
            "can_send_announcements",
            "valid_from",
            "valid_to",
        ]

        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "role_type": forms.Select(attrs={"class": "form-control"}),
            "assigned_groups": forms.SelectMultiple(
                attrs={"class": "form-control", "size": 5, "multiple": True}
            ),
            "permissions_granted": forms.SelectMultiple(
                attrs={"class": "form-control", "size": 5, "multiple": True}
            ),
            "valid_from": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "valid_to": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter users without roles
        existing_roles = UserRole.objects.values_list("user", flat=True)
        if self.instance.pk:
            # If editing, include current user
            existing_roles = existing_roles.exclude(user=self.instance.user)
        self.fields["user"].queryset = (
            CustomUser.objects.filter(is_active=True)
            .exclude(id__in=existing_roles)
            .order_by("last_name", "first_name")
        )

        # make the fields conditional based on roles
        self.fields["assigned_groups"].required = False
        self.fields["permissions_granted"].required = False


class GroupLeaderAssignmentForm(forms.Form):
    """Form for assigning group leaders"""

    leaders = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=forms.SelectMultiple(
            attrs={"class": "form-control", "size": 5, "multiple": True}
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        group = kwargs.pop("group", None)
        super().__init__(*args, **kwargs)

        if group:
            # Only show active members who aren't already leaders of this group
            self.fields["leaders"].queryset = CustomUser.objects.filter(
                is_active=True, status__in=["active", "visitor"]
            ).order_by("last_name", "first_name")
            self.fields["leaders"].initial = group.leaders.all()

    def clean_leaders(self):
        leaders = self.cleaned_data.get("leaders")
        # enforce max 3 leaders per group
        if leaders and leaders.count() > 3:
            raise ValidationError("Group can have at most 3 leaders")
        return leaders
