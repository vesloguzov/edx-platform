"""
Tests for the certificates models.
"""

from django.test import TestCase
from django.core.urlresolvers import reverse

from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from student.tests.factories import UserFactory
from certificates.models import CertificateStatuses, GeneratedCertificate, certificate_status_for_student

import certificates.views
from factories import GeneratedCertificateFactory


class CertificatesModelTest(TestCase):
    """
    Tests for the GeneratedCertificate model
    """

    def test_certificate_status_for_student(self):
        student = UserFactory()
        course = CourseFactory.create(org='edx', number='verified', display_name='Verified Course')

        certificate_status = certificate_status_for_student(student, course.id)
        self.assertEqual(certificate_status['status'], CertificateStatuses.unavailable)
        self.assertEqual(certificate_status['mode'], GeneratedCertificate.MODES.honor)

class CertificateServeTest(ModuleStoreTestCase):
    """
    Test for nginx-protected certificates storage
    """
    def setUp(self):
        self.student = UserFactory()
        self.course = CourseFactory.create(org='edx', number='honor', display_name='Honor Course')
        self.client.login(username=self.student.username, password="test")
        self.url = reverse('serve_certificate', kwargs={'course_id': self.course.id.to_deprecated_string()})

    def test_serve_certificate(self):
        protected_url = certificates.views._certificate_protected_url(self.course, self.student)

        certificate = GeneratedCertificateFactory(
                user=self.student, course_id=self.course.id,
                status = CertificateStatuses.downloadable,
                download_url=protected_url)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('X-Accel-Redirect'))
        self.assertEqual(response['X-Accel-Redirect'], protected_url)

    def test_unavailable_certificate(self):
        certificate = GeneratedCertificateFactory(user=self.student, course_id=self.course.id)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_missing_certificate(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
