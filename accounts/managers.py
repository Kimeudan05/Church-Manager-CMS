from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """Custom manager for CustomUser model"""

    def create_user(self, email, username, password=None, **extra_fields):
        """Create and save a user with the given username,email and password."""

        if not email:
            raise ValueError(_("The email field must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, username, password, **extra_fields)

    def active_members(self):
        """Return active members"""
        return self.filter(status="active", is_active=True)

    def visitors(self):
        """Return visitors"""
        return self.filter(status="visitor", is_active=True)

    def by_group_type(self, group_type):
        """Return members by group type"""
        return self.filter(
            memberships__group__group_type=group_type, is_active=True
        ).distinct()
