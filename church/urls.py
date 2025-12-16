"""
URL configuration for church project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Home
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    # App URLs
    path("accounts/", include("accounts.urls")),
    path("groups/", include("groups.urls")),
    path("events/", include("events.urls")),
    # path('announcements/', include('announcements.urls')),
    path("sermons/", include("sermons.urls")),
    # path('curriculum/', include('curriculum.urls')),
    path("projects/", include("projects.urls")),
    path("dashboard/", include("dashboard.urls")),
    # Third-party
    # path("api-auth/", include("rest_framework.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
