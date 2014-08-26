"""
Report storage views
"""
import os.path

from django_future.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.conf import settings

from instructor_task.models import ReportStore
from courseware.access import has_access
from courseware.courses import get_course_by_id

from opaque_keys.edx.locations import SlashSeparatedCourseKey


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def serve_report(request, course_id, filename):
    """
    Serve grade reports from local filesystem using nginx X-Accell-Redirect header.
    Imply that the view is enabled only if ReportStore is instance of LocalFSReportStore.
    """
    course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
    course = get_course_by_id(course_key, depth=None)
    if not has_access(request.user, 'staff', course):
        return HttpResponseForbidden()

    store = ReportStore.from_config()
    store_filepath = store.path_to(course_key, filename)

    if not os.path.exists(store_filepath):
        raise Http404()

    return _report_response(store.protected_url_for(course_key, filename), filename)

def _report_response(protected_url, filename):
    response = HttpResponse()
    response['X-Accel-Redirect'] = protected_url
    response['Content-Type'] = 'text/csv'
    response['Content-Disposition'] = 'attachment;filename=' + filename
    return response
