"""Tests for the Zendesk and HelpDeskEddy"""

from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from student.tests.factories import UserFactory
from util import views
from zendesk import ZendeskError
from util import helpdeskeddy
import json
import mock

from student.tests.test_microsite import fake_microsite_get_value


class SubmitFeedbackTest(object):
    """
    Base class for feedback submission backends
    """
    def _setUp(self):
        """Set up data for the test case"""
        self._request_factory = RequestFactory()
        self._anon_user = AnonymousUser()
        self._auth_user = UserFactory.create(
            email="test@edx.org",
            username="test",
            profile__name="Test User"
        )
        # This contains issue_type and course_id to ensure that tags are submitted correctly
        self._anon_fields = {
            "email": "test@edx.org",
            "name": "Test User",
            "subject": "a subject",
            "details": "some details",
            "issue_type": "test_issue",
            "course_id": "test_course"
        }
        # This does not contain issue_type nor course_id to ensure that they are optional
        self._auth_fields = {"subject": "a subject", "details": "some details"}

    def _get_error(self, *args, **kwargs):
        raise NotImplementedError

    def _build_and_run_request(self, user, fields):
        """
        Generate a request and invoke the view, returning the response.

        The request will be a POST request from the given `user`, with the given
        `fields` in the POST body.
        """
        req = self._request_factory.post(
            "/submit_feedback",
            data=fields,
            HTTP_REFERER="test_referer",
            HTTP_USER_AGENT="test_user_agent",
            REMOTE_ADDR="1.2.3.4",
            SERVER_NAME="test_server",
        )
        req.user = user
        return views.submit_feedback(req)

    def _assert_bad_request(self, response, field, feedback_backend_mock_class, datadog_mock):
        """
        Assert that the given `response` contains correct failure data.

        It should have a 400 status code, and its content should be a JSON
        object containing list of items with `field` and an `error`.
        """
        self.assertEqual(response.status_code, 400)
        resp_json = json.loads(response.content)
        self.assertIn(field, resp_json)
        # There should be absolutely no interaction with feedback backend
        self.assertFalse(feedback_backend_mock_class.return_value.mock_calls)
        self.assertFalse(datadog_mock.mock_calls)

    def _test_bad_request_omit_field(self, user, fields, omit_field, feedback_backend_mock_class, datadog_mock):
        """
        Invoke the view with a request missing a field and assert correctness.

        The request will be a POST request from the given `user`, with POST
        fields taken from `fields` minus the entry specified by `omit_field`.
        The response should have a 400 (bad request) status code and specify
        the invalid field and an error message, and the Zendesk API should not
        have been invoked.
        """
        filtered_fields = {k: v for (k, v) in fields.items() if k != omit_field}
        resp = self._build_and_run_request(user, filtered_fields)
        self._assert_bad_request(resp, omit_field, feedback_backend_mock_class, datadog_mock)

    def _test_bad_request_omit_multiple_fields(self, user, fields, omit_fields, feedback_backend_mock_class, datadog_mock):
        """
        Just like _test_bad_request_omit_field, but omitting multiple fields.
        """
        filtered_fields = {k: v for (k, v) in fields.items() if k not in omit_fields}
        resp = self._build_and_run_request(user, filtered_fields)
        for field in omit_fields:
            self._assert_bad_request(resp, field, feedback_backend_mock_class, datadog_mock)

    def _test_bad_request_empty_field(self, user, fields, empty_field, feedback_backend_mock_class, datadog_mock):
        """
        Invoke the view with an empty field and assert correctness.

        The request will be a POST request from the given `user`, with POST
        fields taken from `fields`, replacing the entry specified by
        `empty_field` with the empty string. The response should have a 400
        (bad request) status code and specify the invalid field and an error
        message, and the Zendesk API should not have been invoked.
        """
        altered_fields = fields.copy()
        altered_fields[empty_field] = ""
        resp = self._build_and_run_request(user, altered_fields)
        self._assert_bad_request(resp, empty_field, feedback_backend_mock_class, datadog_mock)

    def _test_bad_request_empty_fields(self, user, fields, empty_fields, feedback_backend_mock_class, datadog_mock):
        """
        Just like _test_bad_request_empty_field, but sending multiple empty fields.
        """
        altered_fields = fields.copy()
        for field in empty_fields:
            altered_fields[field] = ""
        resp = self._build_and_run_request(user, altered_fields)
        for field in empty_fields:
            self._assert_bad_request(resp, field, feedback_backend_mock_class, datadog_mock)

    def _test_success(self, user, fields):
        """
        Generate a request, invoke the view, and assert success.

        The request will be a POST request from the given `user`, with the given
        `fields` in the POST body. The response should have a 200 (success)
        status code.
        """
        resp = self._build_and_run_request(user, fields)
        self.assertEqual(resp.status_code, 200)

    def _assert_datadog_called(self, datadog_mock, with_tags):
        expected_datadog_calls = [
            mock.call.increment(
                views.DATADOG_FEEDBACK_METRIC,
                tags=(["course_id:test_course", "issue_type:test_issue"] if with_tags else [])
            )
        ]
        self.assertEqual(datadog_mock.mock_calls, expected_datadog_calls)

    def test_bad_request_anon_user_no_name(self, feedback_backend_mock_class, datadog_mock):
        """Test a request from an anonymous user not specifying `name`."""
        self._test_bad_request_omit_field(self._anon_user, self._anon_fields, "name", feedback_backend_mock_class, datadog_mock)
        self._test_bad_request_empty_field(self._anon_user, self._anon_fields, "name", feedback_backend_mock_class, datadog_mock)

    def test_bad_request_anon_user_no_email(self, feedback_backend_mock_class, datadog_mock):
        """Test a request from an anonymous user not specifying `email`."""
        self._test_bad_request_omit_field(self._anon_user, self._anon_fields, "email", feedback_backend_mock_class, datadog_mock)
        self._test_bad_request_empty_field(self._anon_user, self._anon_fields, "email", feedback_backend_mock_class, datadog_mock)

    def test_bad_request_anon_user_invalid_email(self, feedback_backend_mock_class, datadog_mock):
        """Test a request from an anonymous user specifying an invalid `email`."""
        fields = self._anon_fields.copy()
        fields["email"] = "This is not a valid email address!"
        resp = self._build_and_run_request(self._anon_user, fields)
        self._assert_bad_request(resp, "email", feedback_backend_mock_class, datadog_mock)

    def test_bad_request_anon_user_no_subject(self, feedback_backend_mock_class, datadog_mock):
        """Test a request from an anonymous user not specifying `subject`."""
        self._test_bad_request_omit_field(self._anon_user, self._anon_fields, "subject", feedback_backend_mock_class, datadog_mock)
        self._test_bad_request_empty_field(self._anon_user, self._anon_fields, "subject", feedback_backend_mock_class, datadog_mock)

    def test_bad_request_anon_user_no_details(self, feedback_backend_mock_class, datadog_mock):
        """Test a request from an anonymous user not specifying `details`."""
        self._test_bad_request_omit_field(self._anon_user, self._anon_fields, "details", feedback_backend_mock_class, datadog_mock)
        self._test_bad_request_empty_field(self._anon_user, self._anon_fields, "details", feedback_backend_mock_class, datadog_mock)

    def test_bad_request_auth_user_no_subject(self, feedback_backend_mock_class, datadog_mock):
        """Test a request from an authenticated user not specifying `subject`."""
        self._test_bad_request_omit_field(self._auth_user, self._auth_fields, "subject", feedback_backend_mock_class, datadog_mock)
        self._test_bad_request_empty_field(self._auth_user, self._auth_fields, "subject", feedback_backend_mock_class, datadog_mock)

    def test_bad_request_auth_user_no_details(self, feedback_backend_mock_class, datadog_mock):
        """Test a request from an authenticated user not specifying `details`."""
        self._test_bad_request_omit_field(self._auth_user, self._auth_fields, "details", feedback_backend_mock_class, datadog_mock)
        self._test_bad_request_empty_field(self._auth_user, self._auth_fields, "details", feedback_backend_mock_class, datadog_mock)

    def test_bad_request_anon_user_multiple_fields_missed(self, feedback_backend_mock_class, datadog_mock):
        """Test a request from an anonymous user not specifying multiple fields."""
        self._test_bad_request_omit_multiple_fields(self._anon_user, self._anon_fields, ['name', 'subject'], feedback_backend_mock_class, datadog_mock)
        self._test_bad_request_empty_fields(self._anon_user, self._anon_fields, ['email', 'details'], feedback_backend_mock_class, datadog_mock)

    def test_bad_request_auth_user_multiple_fields_missed(self, feedback_backend_mock_class, datadog_mock):
        """Test a request from an anonymous user not specifying multiple fields."""
        self._test_bad_request_omit_multiple_fields(self._auth_user, self._auth_fields, ['subject', 'details'], feedback_backend_mock_class, datadog_mock)
        self._test_bad_request_empty_fields(self._auth_user, self._auth_fields, ['subject', 'details'], feedback_backend_mock_class, datadog_mock)

    def test_get_request(self, feedback_backend_mock_class, datadog_mock):
        """Test that a GET results in a 405 even with all required fields"""
        req = self._request_factory.get("/submit_feedback", data=self._anon_fields)
        req.user = self._anon_user
        resp = views.submit_feedback(req)
        self.assertEqual(resp.status_code, 405)
        self.assertIn("Allow", resp)
        self.assertEqual(resp["Allow"], "POST")
        # There should be absolutely no interaction with Zendesk
        self.assertFalse(feedback_backend_mock_class.mock_calls)
        self.assertFalse(datadog_mock.mock_calls)

    def test_feedback_backend_error_on_create(self, feedback_backend_mock_class, datadog_mock):
        """
        Test Zendesk returning an error on ticket creation.

        We should return a 500 error with no body
        """
        err = self._get_error(msg="", error_code=404)
        feedback_backend_mock_instance = feedback_backend_mock_class.return_value
        feedback_backend_mock_instance.create_ticket.side_effect = err
        resp = self._build_and_run_request(self._anon_user, self._anon_fields)
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.content)
        self._assert_datadog_called(datadog_mock, with_tags=True)

    @mock.patch.dict("django.conf.settings.FEATURES", {"ENABLE_FEEDBACK_SUBMISSION": False})
    def test_not_enabled(self, feedback_backend_mock_class, datadog_mock):
        """
        Test for feedback submission not enabled in `settings`.

        We should raise Http404.
        """
        with self.assertRaises(Http404):
            self._build_and_run_request(self._anon_user, self._anon_fields)


@mock.patch.dict("django.conf.settings.FEATURES", {"ENABLE_FEEDBACK_SUBMISSION": True})
@override_settings(ZENDESK_URL="dummy", ZENDESK_USER="dummy", ZENDESK_API_KEY="dummy")
@mock.patch("util.views.dog_stats_api")
@mock.patch("util.views._ZendeskApi", autospec=True)
def ZendeskSubmitFeedbackTest(SubmitFeedbackTest, TestCase):
    def setUp(self):
        super(ZendeskSubmitFeedbackTest, self).setUp()
        # run common SubmitFeedbackTest setup
        self._setUp()

    def _get_error(self, *args, **kwargs):
        return ZendeskError(*args, **kwargs)

    def test_valid_request_anon_user(self, feedback_backend_mock_class, datadog_mock):
        """
        Test a valid request from an anonymous user.

        The response should have a 200 (success) status code, and a ticket with
        the given information should have been submitted via the Zendesk API.
        """
        zendesk_mock_instance = feedback_backend_mock_class.return_value
        zendesk_mock_instance.create_ticket.return_value = 42
        self._test_success(self._anon_user, self._anon_fields)
        expected_zendesk_calls = [
            mock.call.create_ticket(
                {
                    "ticket": {
                        "requester": {"name": "Test User", "email": "test@edx.org"},
                        "subject": "a subject",
                        "comment": {"body": "some details"},
                        "tags": ["test_course", "test_issue", "LMS"]
                    }
                }
            ),
            mock.call.update_ticket(
                42,
                {
                    "ticket": {
                        "comment": {
                            "public": False,
                            "body":
                            "Additional information:\n\n"
                            "Client IP: 1.2.3.4\n"
                            "Host: test_server\n"
                            "Page: test_referer\n"
                            "Browser: test_user_agent"
                        }
                    }
                }
            )
        ]
        self.assertEqual(zendesk_mock_instance.mock_calls, expected_zendesk_calls)
        self._assert_datadog_called(datadog_mock, with_tags=True)

    @mock.patch("microsite_configuration.microsite.get_value", fake_microsite_get_value)
    def test_valid_request_anon_user_microsite(self, zendesk_mock_class, datadog_mock):
        """
        Test a valid request from an anonymous user to a mocked out microsite

        The response should have a 200 (success) status code, and a ticket with
        the given information should have been submitted via the Zendesk API with the additional
        tag that will come from microsite configuration
        """
        zendesk_mock_instance = zendesk_mock_class.return_value
        zendesk_mock_instance.create_ticket.return_value = 42
        self._test_success(self._anon_user, self._anon_fields)
        expected_zendesk_calls = [
            mock.call.create_ticket(
                {
                    "ticket": {
                        "requester": {"name": "Test User", "email": "test@edx.org"},
                        "subject": "a subject",
                        "comment": {"body": "some details"},
                        "tags": ["test_course", "test_issue", "LMS", "whitelabel_fakeorg"]
                    }
                }
            ),
            mock.call.update_ticket(
                42,
                {
                    "ticket": {
                        "comment": {
                            "public": False,
                            "body":
                            "Additional information:\n\n"
                            "Client IP: 1.2.3.4\n"
                            "Host: test_server\n"
                            "Page: test_referer\n"
                            "Browser: test_user_agent"
                        }
                    }
                }
            )
        ]
        self.assertEqual(zendesk_mock_instance.mock_calls, expected_zendesk_calls)
        self._assert_datadog_called(datadog_mock, with_tags=True)

    def test_valid_request_auth_user(self, feedback_backend_mock_class, datadog_mock):
        """
        Test a valid request from an authenticated user.

        The response should have a 200 (success) status code, and a ticket with
        the given information should have been submitted via the Zendesk API.
        """
        zendesk_mock_instance = feedback_backend_mock_class.return_value
        zendesk_mock_instance.create_ticket.return_value = 42
        self._test_success(self._auth_user, self._auth_fields)
        expected_zendesk_calls = [
            mock.call.create_ticket(
                {
                    "ticket": {
                        "requester": {"name": "Test User", "email": "test@edx.org"},
                        "subject": "a subject",
                        "comment": {"body": "some details"},
                        "tags": ["LMS"]
                    }
                }
            ),
            mock.call.update_ticket(
                42,
                {
                    "ticket": {
                        "comment": {
                            "public": False,
                            "body":
                            "Additional information:\n\n"
                            "username: test\n"
                            "Client IP: 1.2.3.4\n"
                            "Host: test_server\n"
                            "Page: test_referer\n"
                            "Browser: test_user_agent"
                        }
                    }
                }
            )
        ]
        self.assertEqual(zendesk_mock_instance.mock_calls, expected_zendesk_calls)
        self._assert_datadog_called(datadog_mock, with_tags=False)

    def test_zendesk_error_on_update(self, zendesk_mock_class, datadog_mock):
        """
        Test for Zendesk returning an error on ticket update.

        If Zendesk returns any error on ticket update, we return a 200 to the
        browser because the update contains additional information that is not
        necessary for the user to have submitted their feedback.
        """
        err = ZendeskError(msg="", error_code=500)
        zendesk_mock_instance = zendesk_mock_class.return_value
        zendesk_mock_instance.update_ticket.side_effect = err
        resp = self._build_and_run_request(self._anon_user, self._anon_fields)
        self.assertEqual(resp.status_code, 200)
        self._assert_datadog_called(datadog_mock, with_tags=True)

    def test_zendesk_not_configured(self, zendesk_mock_class, datadog_mock):
        """
        Test for Zendesk not fully configured in `settings`.

        For each required configuration parameter, test that setting it to
        `None` causes an otherwise valid request to return a 500 error.
        """
        def test_case(missing_config):
            with mock.patch(missing_config, None):
                with self.assertRaises(Exception):
                    self._build_and_run_request(self._anon_user, self._anon_fields)

        test_case("django.conf.settings.ZENDESK_URL")
        test_case("django.conf.settings.ZENDESK_USER")
        test_case("django.conf.settings.ZENDESK_API_KEY")


@mock.patch.dict("django.conf.settings.FEATURES", {"ENABLE_FEEDBACK_SUBMISSION": True})
@override_settings(FEEDBACK_BACKEND='helpdeskeddy', HELPDESKEDDY_URL="http://dummy", HELPDESKEDDY_API_KEY="dummy", HELPDESKEDDY_DEPART=1)
@mock.patch("util.views.dog_stats_api")
@mock.patch("util.helpdeskeddy.HelpDeskEddyAPI", autospec=True)
class HelpDeskEddySubmitFeedbackTest(SubmitFeedbackTest, TestCase):
    def setUp(self):
        super(HelpDeskEddySubmitFeedbackTest, self).setUp()
        # run common SubmitFeedbackTest setup
        self._setUp()

    def _get_error(self, *args, **kwargs):
        return helpdeskeddy.HelpDeskEddyError(*args, **kwargs)

    def test_valid_request_anon_user(self, helpdeskeddy_mock_class, datadog_mock):
        """
        Test a valid request from an anonymous user.

        The response should have a 200 (success) status code, and a ticket with
        the given information should have been submitted via the Zendesk API.
        """
        helpdeskeddy_mock_instance = helpdeskeddy_mock_class.return_value
        helpdeskeddy_mock_instance.get_or_create_user.return_value = 42
        self._test_success(self._anon_user, self._anon_fields)
        expected_calls = [
            mock.call.get_or_create_user("test@edx.org", "Test User"),
            mock.call.create_ticket(42, u"a subject", u"some details\n\n#test_course #test_issue #LMS")
        ]
        self.assertEqual(helpdeskeddy_mock_instance.mock_calls, expected_calls)
        self._assert_datadog_called(datadog_mock, with_tags=True)

    @mock.patch("microsite_configuration.microsite.get_value", fake_microsite_get_value)
    def test_valid_request_anon_user_microsite(self, helpdeskeddy_mock_class, datadog_mock):
        """
        Test a valid request from an anonymous user to a mocked out microsite

        The response should have a 200 (success) status code, and a ticket with
        the given information should have been submitted via the HelpDeskEddy API with the additional
        tag that will come from microsite configuration
        """
        helpdeskeddy_mock_instance = helpdeskeddy_mock_class.return_value
        helpdeskeddy_mock_instance.get_or_create_user.return_value = 42
        self._test_success(self._anon_user, self._anon_fields)
        expected_helpdeskeddy_calls = [
            mock.call.get_or_create_user(u"test@edx.org", u"Test User"),
            mock.call.create_ticket(42, u"a subject", u"some details\n\n#test_course #test_issue #LMS #whitelabel_fakeorg")
        ]
        self.assertEqual(helpdeskeddy_mock_instance.mock_calls, expected_helpdeskeddy_calls)
        self._assert_datadog_called(datadog_mock, with_tags=True)

    def test_valid_request_auth_user(self, feedback_backend_mock_class, datadog_mock):
        """
        Test a valid request from an authenticated user.

        The response should have a 200 (success) status code, and a ticket with
        the given information should have been submitted via the HelpDeskEddy API.
        """
        helpdeskeddy_mock_instance = feedback_backend_mock_class.return_value
        helpdeskeddy_mock_instance.get_or_create_user.return_value = 42
        self._test_success(self._auth_user, self._auth_fields)
        expected_helpdeskeddy_calls = [
            mock.call.get_or_create_user("test@edx.org", "Test User"),
            mock.call.create_ticket(42, u"a subject", u"some details\n\n#LMS")
        ]
        self.assertEqual(helpdeskeddy_mock_instance.mock_calls, expected_helpdeskeddy_calls)
        self._assert_datadog_called(datadog_mock, with_tags=False)

    def test_helpdeskeddy_not_configured(self, helpdeskeddy_mock_class, datadog_mock):
        """
        Test for HelpDeskEddy not fully configured in `settings`.

        For each required configuration parameter, test that setting it to
        `None` causes an otherwise valid request to return a 500 error.
        """
        def test_case(missing_config):
            with override_settings(**{missing_config: None}):
                reload(helpdeskeddy)
                with self.assertRaises(Exception):
                    self._build_and_run_request(self._anon_user, self._anon_fields)

        test_case("HELPDESKEDDY_URL")
        test_case("HELPDESKEDDY_API_KEY")
