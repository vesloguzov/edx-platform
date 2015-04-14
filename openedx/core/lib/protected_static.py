"""
HttpResponse creation for nginx X-Accel-Redirect protected static files
"""

from django.http import HttpResponse

def protected_static_response(protected_url, filename, content_type='application/octet-stream'):
    response = HttpResponse()
    response['X-Accel-Redirect'] = protected_url
    response['Content-Type'] = content_type
    response['Content-Disposition'] = 'attachment;filename=' + filename
    return response
