from django.db import models
from django.contrib.auth.models import AbstractUser, Permission, Group as AuthGroup
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# user the custom manager
from .managers import CustomUserManager

objects = CustomUserManager()


class CustomUser(AbstractUser):
    """Extended User model for church members"""

    MEMBERS_STATUS = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("visitor", "Visitor"),
        ("away", "Away"),
    ]
    phone = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    baptism_date = models.DateField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    member_since = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=MEMBERS_STATUS, default="visitor")

    # for family relationship
    spouse = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="married_to",
    )
    parents = models.ManyToManyField(
        "self",
        related_name="children",
        blank=True,
        symmetrical=False,
        limit_choices_to={"is_active": True},
    )

    # Additional fields
    occupation = models.CharField(max_length=100, blank=True, null=True)
    marital_status = models.CharField(
        max_length=20,
        choices=[
            ("single", "Single"),
            ("married", "Married"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
        ],
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Member"
        verbose_name_plural = "Members"
        permissions = [
            ("can_view_members", "Can view all members"),
            ("can_edit_members", "Can edit members"),
            ("can_delete_members", "Can delete members"),
        ]
        ordering = ["-date_joined", "last_name"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

    def get_full_name(self):
        """Return full name with a proper fallback"""
        full_name = super().get_full_name()
        return full_name if full_name.strip() else self.username

    def clean(self):
        """Custom validation"""
        if self.spouse == self:
            raise ValidationError({"spouse": "You cannot be your own spouse"})
        return super().clean()

    @property
    def age(self):
        """Calculate age from date_of_birth"""
        from django.utils import timezone

        if self.date_of_birth:
            today = timezone.now().date()
            return (
                today.year
                - self.date_of_birth.year
                - (
                    (today.month, today.day)
                    < (self.date_of_birth.month, self.date_of_birth.day)
                )
            )
        return None

    def get_primary_group(self):
        """Get the member's primary group"""
        from groups.models import Membership

        try:
            return Membership.objects.get(member=self, is_primary=True).group
        except Membership.DoesNotExist:
            return None
