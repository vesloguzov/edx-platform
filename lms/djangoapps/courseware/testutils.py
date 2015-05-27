"""
Common test utilities for courseware functionality
"""

from abc import ABCMeta, abstractmethod
from datetime import datetime
from django.core.urlresolvers import reverse
from mock import patch

from student.tests.factories import UserFactory, CourseEnrollmentFactory
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory


class RenderXBlockTestMixin(object):
    """
    Mixin for testing the courseware.render_xblock function.
    It can be used for testing any higher-level endpoint that calls this method.
    """
    __metaclass__ = ABCMeta

    # DOM elements that appear in the LMS Courseware,
    # but are excluded from the xBlock-only rendering.
    COURSEWARE_CHROME_HTML_ELEMENTS = [
        '<header id="open_close_accordion"',
        '<ol class="course-tabs"',
        '<footer id="footer-openedx"',
        '<div class="window-wrap"',
        '<div class="preview-menu"',
    ]

    # DOM elements that appear in an xBlock,
    # but are excluded from the xBlock-only rendering.
    XBLOCK_REMOVED_HTML_ELEMENTS = [
        '<div class="wrap-instructor-info"',
    ]

    def setUp(self):
        super(RenderXBlockTestMixin, self).setUp()
        self.course = CourseFactory.create()
        chapter = ItemFactory.create(parent=self.course, category='chapter')
        self.html_block = ItemFactory.create(
            parent=chapter,
            category='html',
            data="<p>Test HTML Content<p>"
        )
        self.user = UserFactory()

    @abstractmethod
    def get_response(self):
        """
        Abstract method to get the response from the endpoint that is being tested.
        """
        pass   # pragma: no cover

    def login(self):
        """
        Logs in the test user.
        """
        self.client.login(username=self.user.username, password='test')

    def setup_user(self, admin=False, enroll=False, login=False):
        """
        Helper method to configure the user.
        """
        if admin:
            self.user.is_staff = True
            self.user.save()  # pylint: disable=no-member

        if enroll:
            CourseEnrollmentFactory(user=self.user, course_id=self.course.id)

        if login:
            self.login()

    def verify_response(self, expected_response_code=200):
        """
        Helper method that calls the endpoint, verifies the expected response code, and returns the response.
        """
        response = self.get_response()
        if expected_response_code == 200:
            self.assertContains(response, self.html_block.data, status_code=expected_response_code)
            for chrome_element in [self.COURSEWARE_CHROME_HTML_ELEMENTS + self.XBLOCK_REMOVED_HTML_ELEMENTS]:
                self.assertNotContains(response, chrome_element)
        else:
            self.assertNotContains(response, self.html_block.data, status_code=expected_response_code)
        return response

    def test_courseware_html(self):
        """
        To verify that the removal of courseware chrome elements is working,
        we include this test here to make sure the chrome elements that should
        be removed actually exist in the full courseware page.
        If this test fails, it's probably because the HTML template for courseware
        has changed and COURSEWARE_CHROME_HTML_ELEMENTS needs to be updated.
        """
        self.setup_user(admin=True, enroll=True, login=True)
        url = reverse('courseware', kwargs={"course_id": unicode(self.course.id)})
        response = self.client.get(url)
        for chrome_element in self.COURSEWARE_CHROME_HTML_ELEMENTS:
            self.assertContains(response, chrome_element)

    def test_success_enrolled_staff(self):
        self.setup_user(admin=True, enroll=True, login=True)
        self.verify_response()

    def test_success_unenrolled_staff(self):
        self.setup_user(admin=True, enroll=False, login=True)
        self.verify_response()

    def test_success_enrolled_student(self):
        self.setup_user(admin=False, enroll=True, login=True)
        self.verify_response()

    def test_fail_unauthenticated(self):
        self.setup_user(admin=False, enroll=True, login=False)
        self.verify_response(expected_response_code=302)

    def test_fail_unenrolled_student(self):
        self.setup_user(admin=False, enroll=False, login=True)
        self.verify_response(expected_response_code=302)

    @patch.dict('django.conf.settings.FEATURES', {'DISABLE_START_DATES': False})
    def test_fail_block_unreleased(self):
        self.setup_user(admin=False, enroll=True, login=True)
        self.html_block.start = datetime.max
        modulestore().update_item(self.html_block, self.user.id)  # pylint: disable=no-member
        self.verify_response(expected_response_code=404)

    def test_fail_block_nonvisible(self):
        self.setup_user(admin=False, enroll=True, login=True)
        self.html_block.visible_to_staff_only = True
        modulestore().update_item(self.html_block, self.user.id)  # pylint: disable=no-member
        self.verify_response(expected_response_code=404)
