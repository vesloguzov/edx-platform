import json
import logging
import sys
from functools import wraps

from django.conf import settings
from django.core.validators import ValidationError, validate_email
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import server_error
from django.http import (Http404, HttpResponse, HttpResponseNotAllowed,
                         HttpResponseServerError)
from django.utils.translation import ugettext_lazy as _

import dogstats_wrapper as dog_stats_api
from edxmako.shortcuts import render_to_response
import zendesk
from microsite_configuration import microsite

import calc
import track.views
import helpdeskeddy

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

log = logging.getLogger(__name__)


def ensure_valid_course_key(view_func):
    """
    This decorator should only be used with views which have argument course_key_string (studio) or course_id (lms).
    If course_key_string (studio) or course_id (lms) is not valid raise 404.
    """
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        course_key = kwargs.get('course_key_string') or kwargs.get('course_id')
        if course_key is not None:
            try:
                CourseKey.from_string(course_key)
            except InvalidKeyError:
                raise Http404

        response = view_func(request, *args, **kwargs)
        return response

    return inner


@requires_csrf_token
def jsonable_server_error(request, template_name='500.html'):
    """
    500 error handler that serves JSON on an AJAX request, and proxies
    to the Django default `server_error` view otherwise.
    """
    if request.is_ajax():
        msg = {"error": "The edX servers encountered an error"}
        return HttpResponseServerError(json.dumps(msg))
    else:
        return server_error(request, template_name=template_name)


def handle_500(template_path, context=None, test_func=None):
    """
    Decorator for view specific 500 error handling.
    Custom handling will be skipped only if test_func is passed and it returns False

    Usage:

        @handle_500(
            template_path='certificates/server-error.html',
            context={'error-info': 'Internal Server Error'},
            test_func=lambda request: request.GET.get('preview', None)
        )
        def my_view(request):
            # Any unhandled exception in this view would be handled by the handle_500 decorator
            # ...

    """
    def decorator(func):
        """
        Decorator to render custom html template in case of uncaught exception in wrapped function
        """
        @wraps(func)
        def inner(request, *args, **kwargs):
            """
            Execute the function in try..except block and return custom server-error page in case of unhandled exception
            """
            try:
                return func(request, *args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                if settings.DEBUG:
                    # In debug mode let django process the 500 errors and display debug info for the developer
                    raise
                elif test_func is None or test_func(request):
                    # Display custom 500 page if either
                    #   1. test_func is None (meaning nothing to test)
                    #   2. or test_func(request) returns True
                    log.exception("Error in django view.")
                    return render_to_response(template_path, context)
                else:
                    # Do not show custom 500 error when test fails
                    raise
        return inner
    return decorator


def calculate(request):
    ''' Calculator in footer of every page. '''
    equation = request.GET['equation']
    try:
        result = calc.evaluator({}, {}, equation)
    except:
        event = {'error': map(str, sys.exc_info()),
                 'equation': equation}
        track.views.server_track(request, 'error:calc', event, page='calc')
        return HttpResponse(json.dumps({'result': 'Invalid syntax'}))
    return HttpResponse(json.dumps({'result': str(result)}))


def _get_feedback_form_errors(request):
    """
    Check all feedback form fields are filled and email is correct.

    Return list of items {'field': field_name, 'error': error_label}.
    """
    errors = {}

    required_fields = ["subject", "details"]
    if not request.user.is_authenticated():
        required_fields += ["name", "email"]
    required_field_errs = {
        "subject": _("Please provide a subject."),
        "details": _("Please provide details."),
        "name": _("Please provide your name."),
        "email": _("Please provide a valid e-mail."),
    }

    for field in required_fields:
        if not request.POST.get(field):
            errors[field] = unicode(required_field_errs[field])

    if "email" in request.POST:
        try:
            validate_email(request.POST["email"])
        except ValidationError:
            errors["email"] = unicode(required_field_errs["email"])

    return errors


def _get_feedback_backend():
    if settings.FEEDBACK_BACKEND.lower() == 'zendesk':
        return ZendeskFeedbackBackend()
    elif settings.FEEDBACK_BACKEND.lower() == 'helpdeskeddy':
        return HelpDeskEddyFeedbackBackend()
    else:
        raise Exception('Feedback backend not configured')


class FeedbackBackend(object):
    required_settings = ()

    def __init__(self):
        if not any(getattr(settings, name) for name in self.required_settings):
            raise Exception('%s enabled but not configured.' % self.name)

    @staticmethod
    def record_feedback(realname, email, subject, details, tags, additional_info):
        raise NotImplementedError


class ZendeskFeedbackBackend(FeedbackBackend):
    name = 'Zendesk'
    required_settings = ('ZENDESK_URL', 'ZENDESK_USER', 'ZENDESK_API_KEY')

    @staticmethod
    def record_feedback(*args, **kwargs):
        return _record_feedback_in_zendesk(*args, **kwargs)


class HelpDeskEddyFeedbackBackend(helpdeskeddy.HelpDeskEddyMixin, FeedbackBackend):
    name = 'HelpDeskEddy'
    required_settings = ('HELPDESKEDDY_URL', 'HELPDESKEDDY_API_KEY')


class _ZendeskApi(object):
    def __init__(self):
        """
        Instantiate the Zendesk API.

        All of `ZENDESK_URL`, `ZENDESK_USER`, and `ZENDESK_API_KEY` must be set
        in `django.conf.settings`.
        """
        self._zendesk_instance = zendesk.Zendesk(
            settings.ZENDESK_URL,
            settings.ZENDESK_USER,
            settings.ZENDESK_API_KEY,
            use_api_token=True,
            api_version=2,
            # As of 2012-05-08, Zendesk is using a CA that is not
            # installed on our servers
            client_args={"disable_ssl_certificate_validation": True}
        )

    def create_ticket(self, ticket):
        """
        Create the given `ticket` in Zendesk.

        The ticket should have the format specified by the zendesk package.
        """
        ticket_url = self._zendesk_instance.create_ticket(data=ticket)
        return zendesk.get_id_from_url(ticket_url)

    def update_ticket(self, ticket_id, update):
        """
        Update the Zendesk ticket with id `ticket_id` using the given `update`.

        The update should have the format specified by the zendesk package.
        """
        self._zendesk_instance.update_ticket(ticket_id=ticket_id, data=update)


def _record_feedback_in_zendesk(realname, email, subject, details, tags, additional_info):
    """
    Create a new user-requested Zendesk ticket.

    Once created, the ticket will be updated with a private comment containing
    additional information from the browser and server, such as HTTP headers
    and user state. Returns a boolean value indicating whether ticket creation
    was successful, regardless of whether the private comment update succeeded.
    """
    zendesk_api = _ZendeskApi()

    additional_info_string = (
        "Additional information:\n\n" +
        "\n".join("%s: %s" % (key, value) for (key, value) in additional_info.items() if value is not None)
    )

    # Tag all issues with LMS to distinguish channel in Zendesk; requested by student support team
    zendesk_tags = list(tags.values()) + ["LMS"]

    # Per edX support, we would like to be able to route white label feedback items
    # via tagging
    white_label_org = microsite.get_value('course_org_filter')
    if white_label_org:
        zendesk_tags = zendesk_tags + ["whitelabel_{org}".format(org=white_label_org)]

    new_ticket = {
        "ticket": {
            "requester": {"name": realname, "email": email},
            "subject": subject,
            "comment": {"body": details},
            "tags": zendesk_tags
        }
    }
    try:
        ticket_id = zendesk_api.create_ticket(new_ticket)
    except zendesk.ZendeskError:
        log.exception("Error creating Zendesk ticket")
        return False

    # Additional information is provided as a private update so the information
    # is not visible to the user.
    ticket_update = {"ticket": {"comment": {"public": False, "body": additional_info_string}}}
    try:
        zendesk_api.update_ticket(ticket_id, ticket_update)
    except zendesk.ZendeskError:
        log.exception("Error updating Zendesk ticket")
        # The update is not strictly necessary, so do not indicate failure to the user
        pass

    return True


DATADOG_FEEDBACK_METRIC = "lms_feedback_submissions"


def _record_feedback_in_datadog(tags):
    datadog_tags = [u"{k}:{v}".format(k=k, v=v) for k, v in tags.items()]
    dog_stats_api.increment(DATADOG_FEEDBACK_METRIC, tags=datadog_tags)


def submit_feedback(request):
    """
    Create a new user-requested ticket, currently implemented with Zendesk.

    If feedback submission is not enabled, any request will raise `Http404`.
    If any configuration parameter (`ZENDESK_URL`, `ZENDESK_USER`, or
    `ZENDESK_API_KEY`) is missing, any request will raise an `Exception`.
    The request must be a POST request specifying `subject` and `details`.
    If the user is not authenticated, the request must also specify `name` and
    `email`. If the user is authenticated, the `name` and `email` will be
    populated from the user's information. If any required parameter is
    missing, a 400 error will be returned indicating which field is missing and
    providing an error message. If Zendesk ticket creation fails, 500 error
    will be returned with no body; if ticket creation succeeds, an empty
    successful response (200) will be returned.
    """
    if not settings.FEATURES.get('ENABLE_FEEDBACK_SUBMISSION', False):
        raise Http404()
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    feedback_backend = _get_feedback_backend()

    additional_info = {}

    errors = _get_feedback_form_errors(request)
    if errors:
        return HttpResponse(json.dumps(errors), status=400)

    subject = request.POST["subject"]
    details = request.POST["details"]
    tags = dict(
        [(tag, request.POST[tag]) for tag in ["issue_type", "course_id"] if tag in request.POST]
    )

    if request.user.is_authenticated():
        realname = request.user.profile.name
        email = request.user.email
        additional_info["username"] = request.user.username
        additional_info["nickname"] = request.user.profile.nickname
    else:
        realname = request.POST["name"]
        email = request.POST["email"]

    for header, pretty in [
        ("HTTP_REFERER", "Page"),
        ("HTTP_USER_AGENT", "Browser"),
        ("REMOTE_ADDR", "Client IP"),
        ("SERVER_NAME", "Host")
    ]:
        additional_info[pretty] = request.META.get(header)

    success = feedback_backend.record_feedback(realname, email, subject, details, tags, additional_info)
    _record_feedback_in_datadog(tags)

    return HttpResponse(status=(200 if success else 500))


def info(request):
    ''' Info page (link from main header) '''
    return render_to_response("info.html", {})


# From http://djangosnippets.org/snippets/1042/
def parse_accept_header(accept):
    """Parse the Accept header *accept*, returning a list with pairs of
    (media_type, q_value), ordered by q values.
    """
    result = []
    for media_range in accept.split(","):
        parts = media_range.split(";")
        media_type = parts.pop(0)
        media_params = []
        q = 1.0
        for part in parts:
            (key, value) = part.lstrip().split("=", 1)
            if key == "q":
                q = float(value)
            else:
                media_params.append((key, value))
        result.append((media_type, tuple(media_params), q))
    result.sort(lambda x, y: -cmp(x[2], y[2]))
    return result


def accepts(request, media_type):
    """Return whether this request has an Accept header that matches type"""
    accept = parse_accept_header(request.META.get("HTTP_ACCEPT", ""))
    return media_type in [t for (t, p, q) in accept]
