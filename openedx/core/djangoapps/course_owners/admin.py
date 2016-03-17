"""
Django admin page for course owners
"""
from django.contrib import admin

from .models import CourseOwnership

admin.site.register(CourseOwnership)
