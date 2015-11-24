"""
Decorators for displaying a form with fields that user is insistently asked to fill
"""

import functools
import datetime

from django.utils.decorators import available_attrs
from django.conf import settings
from django.utils.formats import get_format

from opaque_keys.edx.locations import SlashSeparatedCourseKey

from courseware.access import has_access

from views import RequiredStudentDataForm


def require_student_data(view_func):
    """
    Decorator for views where form with personal info request is shown before content access
    """
    @functools.wraps(view_func, assigned=available_attrs(view_func))
    def decorator(request, *args, **kwargs):
        course_id = kwargs.get('course_id') or (len(args) > 0 and args[0])
        if settings.REQUIRE_STUDENT_DATA_FOR_COURSEWARE and _require_student_data(request, course_id):
            form = request._required_student_data_form = RequiredStudentDataForm(instance=request.user.profile)
        return view_func(request, *args, **kwargs)
    return decorator


def _require_student_data(request, course_id):
    if not request.user.is_authenticated():
        return False

    if course_id:
        course_id = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        staff_access = has_access(request.user, 'staff', course_id)
    else:
        staff_access = request.user.is_staff
    if staff_access:
        return False

    if _required_data_complete(request.user):
        return False

    student_data_requested = request.session.get('REQUIRE_USER_DATA', False)
    return (not student_data_requested
            or student_data_requested < datetime.datetime.now())


def _required_data_complete(user):
    profile = user.profile
    return ((profile.first_name or profile.last_name)
            and profile.birthdate
            and profile.city)
