"""Views and forms for displaying a form with fields that user is insistently asked to fill"""

import functools
import datetime

from django import forms
from django.http import Http404
from django.utils.decorators import available_attrs
from django.views.decorators.http import require_POST
from django_future.csrf import ensure_csrf_cookie
from django.conf import settings

from opaque_keys.edx.locations import SlashSeparatedCourseKey

from student.models import UserProfile
from courseware.access import has_access
from util.json_request import JsonResponse

def require_student_data(view_func):
    @functools.wraps(view_func, assigned=available_attrs(view_func))
    def decorator(request, *args, **kwargs):
        course_id = kwargs.get('course_id') or (len(args) > 0 and args[0])
        if _require_student_data(request, course_id):
            request._required_student_data_form = RequiredStudentDataForm(instance=request.user.profile)
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
        # TODO: turn on
        # return False
        pass

    if _required_data_complete(request.user):
        return False

    student_data_requested = request.session.get('REQUIRE_USER_DATA', False)
    return (not student_data_requested
            or student_data_requested < datetime.datetime.now())

def _required_data_complete(user):
    profile = user.profile
    return (profile.first_name or profile.last_name) and profile.birthdate

# ask for data:
# is authenticated
# is not staff for the course
# has empty fields
# request.session['REQUIRE_USER_DATA']


def require_authenticated_or_404(view_func):
    @functools.wraps(view_func, assigned=available_attrs(view_func))
    def decorator(request, *args, **kwargs):
        if not request.user.is_authenticated():
            raise Http404
        else:
            return view_func(request, *args, **kwargs)
    return decorator


@ensure_csrf_cookie
@require_POST
@require_authenticated_or_404
def update_required_data(request):
    form = RequiredStudentDataForm(request.POST, instance=request.user.profile)
    if form.is_valid():
        form.save()
        # add a timeout for next check if user removes some data in future
        _postpone_student_data_update(request.session)
        return JsonResponse({'success': True})
    else:
        return JsonResponse({
            'success': False,
            'errors': _form_errors_to_json(form),
        }, status=400)


@ensure_csrf_cookie
@require_POST
@require_authenticated_or_404
def postpone_required_data_update(request):
    _postpone_student_data_update(request.session)
    return JsonResponse({'success': True})

def _postpone_student_data_update(session):
    timeout = getattr(settings, 'USER_DATA_REQUEST_TIMEOUT', datetime.timedelta(hours=24))
    session['REQUIRE_USER_DATA'] = datetime.datetime.now() + timeout


class RequiredStudentDataForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('first_name', 'last_name', 'birthdate')


def _form_errors_to_json(form):
    errors = []
    for field_name, error_list in form._errors.iteritems():
        if field_name == forms.forms.NON_FIELD_ERRORS:
            field_id = ''
        else:
            field_id = form.auto_id % field_name
        errors.append({
            'field': field_id,
            'errors': ', '.join(error_list)
        })
    return errors
