"""
Views related to course owners
"""
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings

from microsite_configuration import microsite

from util.cache import cache_if_anonymous
from edxmako.shortcuts import render_to_response

from .models import CourseOwnership


@ensure_csrf_cookie
@cache_if_anonymous()
@require_http_methods(['GET'])
def owners_list(request):  # pylint: disable=unused-argument
    """
    List all users owning the course(s)
    """
    # TODO: add information about owners having accessible courses
    owner_ids = CourseOwnership.objects.values_list('user', flat=True)
    owners = User.objects.filter(id__in=owner_ids).order_by('username')
    return render_to_response('owners.html', {'owners': owners})


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
