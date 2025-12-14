from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.conf import settings
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetView,
    PasswordResetConfirmView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, UpdateView, TemplateView

from .forms import RegistrationForm, ProfileUpdateForm


class CustomLoginView(SuccessMessageMixin, LoginView):
    """custom login view"""

    template_name = "accounts/login.html"
    success_message = "Welcome back! You are now logged in."

    def get_success_url(self):
        user = self.request.user

        # Admin users based on church_role
        if hasattr(user, "church_role") and user.church_role.role_type in [
            "super_admin",
            "church_admin",
        ]:
            return reverse_lazy("dashboard:admin")

        # Group leaders
        if (
            hasattr(user, "church_role")
            and user.church_role.role_type == "group_leader"
        ):
            return reverse_lazy("dashboard:group_leader")

        # Default member dashboard
        return reverse_lazy("dashboard:member")


class RegistrationView(SuccessMessageMixin, CreateView):
    """User registration view"""

    model = settings.AUTH_USER_MODEL
    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Registration successful. You can now log in."

    def form_valid(self, form):
        """If form is valid, save user and set default role"""
        user = form.save()

        # Create default role for new members

        from groups.models import UserRole

        UserRole.objects.create(user=user, role_type="member")

        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    """User Profile view"""

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update user profile"""

    model = settings.AUTH_USER_MODEL
    form_class = ProfileUpdateForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:profile")
    success_message = "Profile updated successfully."

    def get_object(self, queryset=...):
        return self.request.user


class CustomPasswordChangeView(
    LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView
):
    """Custom password change view"""

    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password_reset_done")
    success_message = (
        "Password reset email has been sent if the email exists in our system."
    )


class CustomPasswordResetView(SuccessMessageMixin, PasswordResetView):
    """Custom Password reset view"""

    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    success_url = reverse_lazy("accounts:password_reset_done")
    success_message = (
        "Password reset email has been send if the email exists in our system."
    )


class CustomPasswordResetConfirmView(SuccessMessageMixin, PasswordResetConfirmView):
    """Custom Password reset confirm view"""

    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Your password has been reset successfully. You can now login with your new password."


class CustomLogoutView(SuccessMessageMixin, LogoutView):
    """Custom logout view with success message"""

    def get_next_page(self):
        messages.success(self.request, "You have been logged out successfully.")
        return super().get_next_page()
