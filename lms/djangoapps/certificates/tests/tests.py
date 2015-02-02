"""
Tests for the certificates models.
"""
from unittest import skip

from mock import patch
from django.conf import settings
from django.test import TestCase
from django.core.urlresolvers import reverse

from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from student.tests.factories import UserFactory
from certificates.models import CertificateStatuses, GeneratedCertificate, certificate_status_for_student
from certificates.tests.factories import GeneratedCertificateFactory

from util.milestones_helpers import (
    set_prerequisite_courses,
    milestones_achieved_by_user,
    seed_milestone_relationship_types,
)


class CertificatesModelTest(ModuleStoreTestCase):
    """
    Tests for the GeneratedCertificate model
    """

    def test_certificate_status_for_student(self):
        student = UserFactory()
        course = CourseFactory.create(org='edx', number='verified', display_name='Verified Course')

        certificate_status = certificate_status_for_student(student, course.id)
        self.assertEqual(certificate_status['status'], CertificateStatuses.unavailable)
        self.assertEqual(certificate_status['mode'], GeneratedCertificate.MODES.honor)

    @patch.dict(settings.FEATURES, {'ENABLE_PREREQUISITE_COURSES': True, 'MILESTONES_APP': True})
    def test_course_milestone_collected(self):
        seed_milestone_relationship_types()
        student = UserFactory()
        course = CourseFactory.create(org='edx', number='998', display_name='Test Course')
        pre_requisite_course = CourseFactory.create(org='edx', number='999', display_name='Pre requisite Course')
        # set pre-requisite course
        set_prerequisite_courses(course.id, [unicode(pre_requisite_course.id)])
        # get milestones collected by user before completing the pre-requisite course
        completed_milestones = milestones_achieved_by_user(student, unicode(pre_requisite_course.id))
        self.assertEqual(len(completed_milestones), 0)

        GeneratedCertificateFactory.create(
            user=student,
            course_id=pre_requisite_course.id,
            status=CertificateStatuses.generating,
            mode='verified'
        )
        # get milestones collected by user after user has completed the pre-requisite course
        completed_milestones = milestones_achieved_by_user(student, unicode(pre_requisite_course.id))
        self.assertEqual(len(completed_milestones), 1)
        self.assertEqual(completed_milestones[0]['namespace'], unicode(pre_requisite_course.id))

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
