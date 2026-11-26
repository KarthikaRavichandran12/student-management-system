"""ASGI config for the Student Management System project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "student_management.settings")

application = get_asgi_application()
