"""
Tests for certificate app views used by the support team.
"""

import json

import ddt
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from opaque_keys.edx.keys import CourseKey
from student.tests.factories import UserFactory
from student.models import CourseEnrollment
from student.roles import GlobalStaff, SupportStaffRole
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory
from certificates.models import GeneratedCertificate, CertificateStatuses

FEATURES_WITH_CERTS_ENABLED = settings.FEATURES.copy()
FEATURES_WITH_CERTS_ENABLED['CERTIFICATES_HTML_VIEW'] = True


class CertificateSupportTestCase(ModuleStoreTestCase):
    """
    Base class for tests of the certificate support views.
    """

    SUPPORT_USERNAME = "support"
    SUPPORT_EMAIL = "support@example.com"
    SUPPORT_PASSWORD = "support"

    STUDENT_USERNAME = "student"
    STUDENT_EMAIL = "student@example.com"
    STUDENT_PASSWORD = "student"

    CERT_COURSE_KEY = CourseKey.from_string("edX/DemoX/Demo_Course")
    COURSE_NOT_EXIST_KEY = CourseKey.from_string("test/TestX/Test_Course_Not_Exist")
    EXISTED_COURSE_KEY_1 = CourseKey.from_string("test1/Test1X/Test_Course_Exist_1")
    EXISTED_COURSE_KEY_2 = CourseKey.from_string("test2/Test2X/Test_Course_Exist_2")
    CERT_GRADE = 0.89
    CERT_STATUS = CertificateStatuses.downloadable
    CERT_MODE = "verified"
    CERT_DOWNLOAD_URL = "http://www.example.com/cert.pdf"

    def setUp(self):
        """
        Create a support team member and a student with a certificate.
        Log in as the support team member.
        """
        super(CertificateSupportTestCase, self).setUp()

        # Create the support staff user
        self.support = UserFactory(
            username=self.SUPPORT_USERNAME,
            email=self.SUPPORT_EMAIL,
            password=self.SUPPORT_PASSWORD,
        )
        SupportStaffRole().add_users(self.support)

        # Create a student
        self.student = UserFactory(
            username=self.STUDENT_USERNAME,
            email=self.STUDENT_EMAIL,
            password=self.STUDENT_PASSWORD,
        )

        # Create certificates for the student
        self.cert = GeneratedCertificate.eligible_certificates.create(
            user=self.student,
            course_id=self.CERT_COURSE_KEY,
            grade=self.CERT_GRADE,
            status=self.CERT_STATUS,
            mode=self.CERT_MODE,
            download_url=self.CERT_DOWNLOAD_URL,
        )

        # Login as support staff
        success = self.client.login(username=self.SUPPORT_USERNAME, password=self.SUPPORT_PASSWORD)
        self.assertTrue(success, msg="Couldn't log in as support staff")


@ddt.ddt
class CertificateSearchTests(CertificateSupportTestCase):
    """
    Tests for the certificate search end-point used by the support team.
    """
    def setUp(self):
        """
        Create a course
        """
        super(CertificateSearchTests, self).setUp()
        self.course = CourseFactory()
        self.course.cert_html_view_enabled = True

        #course certificate configurations
        certificates = [
            {
                'id': 1,
                'name': 'Name 1',
                'description': 'Description 1',
                'course_title': 'course_title_1',
                'signatories': [],
                'version': 1,
                'is_active': True
            }
        ]

        self.course.certificates = {'certificates': certificates}
        self.course.save()  # pylint: disable=no-member
        self.store.update_item(self.course, self.user.id)

    @ddt.data(
        (GlobalStaff, True),
        (SupportStaffRole, True),
        (None, False),
    )
    @ddt.unpack
    def test_access_control(self, role, has_access):
        # Create a user and log in
        user = UserFactory(username="foo", password="foo")
        success = self.client.login(username="foo", password="foo")
        self.assertTrue(success, msg="Could not log in")

        # Assign the user to the role
        if role is not None:
            role().add_users(user)

        # Retrieve the page
        response = self._search("foo")

        if has_access:
            self.assertContains(response, json.dumps([]))
        else:
            self.assertEqual(response.status_code, 403)

    @ddt.data(
        (CertificateSupportTestCase.STUDENT_USERNAME, True),
        (CertificateSupportTestCase.STUDENT_EMAIL, True),
        ("bar", False),
        ("bar@example.com", False),
    )
    @ddt.unpack
    def test_search(self, query, expect_result):
        response = self._search(query)
        self.assertEqual(response.status_code, 200)

        results = json.loads(response.content)
        self.assertEqual(len(results), 1 if expect_result else 0)

    def test_results(self):
        response = self._search(self.STUDENT_USERNAME)
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)

        self.assertEqual(len(results), 1)
        retrieved_cert = results[0]

        self.assertEqual(retrieved_cert["username"], self.STUDENT_USERNAME)
        self.assertEqual(retrieved_cert["course_key"], unicode(self.CERT_COURSE_KEY))
        self.assertEqual(retrieved_cert["created"], self.cert.created_date.isoformat())
        self.assertEqual(retrieved_cert["modified"], self.cert.modified_date.isoformat())
        self.assertEqual(retrieved_cert["grade"], unicode(self.CERT_GRADE))
        self.assertEqual(retrieved_cert["status"], self.CERT_STATUS)
        self.assertEqual(retrieved_cert["type"], self.CERT_MODE)
        self.assertEqual(retrieved_cert["download_url"], self.CERT_DOWNLOAD_URL)

    @override_settings(FEATURES=FEATURES_WITH_CERTS_ENABLED)
    def test_download_link(self):
        self.cert.course_id = self.course.id  # pylint: disable=no-member
        self.cert.download_url = ''
        self.cert.save()

        response = self._search(self.STUDENT_USERNAME)
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)

        self.assertEqual(len(results), 1)
        retrieved_cert = results[0]

        self.assertEqual(
            retrieved_cert["download_url"],
            reverse(
                'certificates:html_view',
                kwargs={"user_id": self.student.id, "course_id": self.course.id}  # pylint: disable=no-member
            )
        )

    def _search(self, query):
        """Execute a search and return the response. """
        url = reverse("certificates:search") + "?query=" + query
        return self.client.get(url)
