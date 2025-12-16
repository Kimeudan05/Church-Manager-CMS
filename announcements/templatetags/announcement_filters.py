from django import template

register = template.Library()


@register.filter
def filter_published(queryset, today):
    return queryset.filter(is_published=True, publish_at__lte=today)


@register.filter
def filter_scheduled(queryset, today):
    return queryset.filter(is_published=True, publish_at__gt=today)


@register.filter
def filter_drafts(queryset):
    return queryset.filter(is_published=False)


@register.filter
def filter_expired(queryset, today):
    return queryset.filter(expires_at__lt=today)


@register.filter
def filter_priority(queryset, priority):
    return queryset.filter(priority=priority)


@register.filter
def contains(queryset, item):
    return item in queryset
