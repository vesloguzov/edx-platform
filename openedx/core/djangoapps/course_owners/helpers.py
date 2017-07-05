"""
Helpers related to course owners
"""
from django.contrib.auth.models import User
from django.conf import settings

from microsite_configuration import microsite

from .models import CourseOwnership


def get_accessible_owner_courses(request, owner):
    """
    Helper method for filtering courses by access and owners
    """

    # prevent calling from other applications
    assert settings.ROOT_URLCONF == 'lms.urls'
    from courseware.courses import get_courses, sort_by_announcement, sort_by_start_date

    courses = get_courses(request.user)

    owned_courses = [o.course_id for o in CourseOwnership.objects.filter(user=owner)]
    courses = [course for course in courses if course.id in owned_courses]

    if microsite.get_value("ENABLE_COURSE_SORTING_BY_START_DATE",
                           settings.FEATURES["ENABLE_COURSE_SORTING_BY_START_DATE"]):
        courses = sort_by_start_date(courses)
    else:
        courses = sort_by_announcement(courses)

    return courses
