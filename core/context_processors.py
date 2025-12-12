from groups.models import ChurchGroup


def church_context(request):
    """Add church-wide context to all templates"""
    context = {}

    if request.user.is_authenticated:
        context["user_groups"] = (
            request.user.groups.all() if hasattr(request.user, "groups") else []
        )
        context["user_role"] = getattr(request.user, "church_role", None)

        # Add church groups for navigation
        context["all_groups"] = ChurchGroup.objects.all()[:8]  # limit for menu

    return context
