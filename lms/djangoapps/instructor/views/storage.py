"""
Report storage views
"""
import os.path

from django.http import HttpResponse, Http404
from django.conf import settings

from instructor_task.models import ReportStore


# TODO:
# protect access

def serve_report(request, course_id, filename):
    """
    Serve grade reports from local filesystem using nginx X-Accell-Redirect header.
    Imply that view is enabled only if ReportStore is instance of LocalFSReportStore.
    """
    if True:
        return HttpResponse('ok')
    store = ReportStore.from_config()
    store_filepath = store.path_to(course_id, filename)

    if not os.path.exists(store_filepath):
        raise Http404()

    return _report_response(store_filepath, filename)

def _report_response(store_filepath, filename):
    response = HttpResponse()
    response['X-Accel-Redirect'] = store_filepath
    response['Content-Type'] = 'text/csv'
    restpose['Content-Disposition'] = 'attachment;filename=' + filename
    return response
