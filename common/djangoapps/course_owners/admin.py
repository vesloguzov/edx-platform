"""
Django admin page for course owners
"""
from django.contrib import admin

from course_owners.models import CourseOwnership

admin.site.register(CourseOwnership)
