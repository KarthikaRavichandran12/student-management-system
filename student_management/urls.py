"""Root URL configuration for the Student Management System."""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def health(request):
    """Lightweight liveness check for uptime monitors."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("health", health, name="health"),
    path("health/", health),
    path("admin/", admin.site.urls),
    path("", include("students.urls")),
]
