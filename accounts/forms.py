from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users in admin"""

    email = forms.EmailField(required=True)
    phone = forms.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ("username", "email", "phone", "first_name", "last_name")

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        # Ensure only digits
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")

        # Ensure length is between 10 and 12
        if not 10 <= len(phone) <= 12:
            raise forms.ValidationError("Phone number must be 10-12 digits long.")

        # Ensure uniqueness
        if CustomUser.objects.filter(phone=phone).exists():
            raise forms.ValidationError("A user with this phone number already exists.")

        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email


class CustomUserChangeForm(UserChangeForm):
    """Form for updating users in admin"""

    class Meta:
        model = CustomUser
        fields = "__all__"


class RegistrationForm(forms.ModelForm):
    """Form for user registration"""

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter password"}
        ),
        help_text="Your password must contain at least 8 characters.",
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm password"}
        ),
    )

    class Meta:
        model = CustomUser
        fields = (
            "username",
            "email",
            "phone",
            "first_name",
            "last_name",
            "date_of_birth",
        )
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Username"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Enter email"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Phone Number"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "First Name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Last Name"}
            ),
            "date_of_birth": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")

        if len(password1) < 8:
            raise ValidationError("Password must be at least 8 characters long")

        return password2

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if CustomUser.objects.filter(phone=phone).exists():
            raise ValidationError("This phone number is already registered.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
            "date_of_birth",
            "profile_picture",
            "occupation",
            "marital_status",
            "emergency_contact",  # Add the name
            "emergency_contact_phone",
            "baptism_date",
        )
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "first name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "last name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "email address"}
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "tel",
                    "pattern": "[0-9]+",
                    "maxlength": "12",
                    "placeholder": "0788XXXXXX",
                    "title": "Enter digits only",
                }
            ),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "date_of_birth": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "occupation": forms.TextInput(attrs={"class": "form-control"}),
            "marital_status": forms.Select(attrs={"class": "form-control"}),
            "baptism_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "profile_picture": forms.FileInput(attrs={"class": "form-control"}),
            "emergency_contact": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Name of who to contact incase of emergency",
                }
            ),
            "emergency_contact_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "class": "form-control",
                    "autocomplete": "tel",
                    "pattern": "[0-9]+",
                    "maxlength": "12",
                    "placeholder": "0788XXXXXX",
                    "title": "Enter digits only",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        # Ensure only digits
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")

        # Ensure length is between 10 and 12
        if not 10 <= len(phone) <= 12:
            raise forms.ValidationError("Phone number must be 10-12 digits long.")

        # Ensure uniqueness excluding the current user
        if CustomUser.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with this phone number already exists.")

        return phone
