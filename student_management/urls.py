"""Root URL configuration for the Student Management System."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("students.urls")),
]
