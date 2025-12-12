from django.db.models.signals import m2m_changed, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from groups.models import ChurchGroup, Membership
from .models import CustomUser

# RULE 1 → A group can have AT MOST 3 leaders


@receiver(m2m_changed, sender=ChurchGroup.leaders.through)
def limit_group_leaders(sender, instance, action, pk_set, **kwargs):
    """Prevent adding more than 3 leaders to group"""
    if action == "pre_add":
        total = instance.leaders.count() + len(pk_set)

        if total > 3:
            raise ValidationError(f"Group {instance.name} can have at most 3 leaders")


# RULE 2 → A member can belong to AT MOST 3 groups
@receiver(m2m_changed, sender=Membership)
def limit_member_groups(sender, instance, **kwargs):
    """Prevent a member from belonging to more than 3 groups"""

    if instance.pk is None:  # only for new memberships
        current = Membership.objects.filter(member=instance.member).count()

        if current >= 3:
            raise ValidationError(
                f"{instance.member.username} already belongs to 3 groups"
            )


# RULE 3 → A member can have ONLY ONE primary group


@receiver(pre_save, sender=Membership)
def enforce_single_primary(sender, instance, **kwargs):
    """Ensure only one primary group per member"""
    if instance.is_primary:
        # remove primary flag from other memberships
        Membership.objects.filter(member=instance.member, is_primary=True).exclude(
            pk=instance.pk
        ).update(is_primary=False)
