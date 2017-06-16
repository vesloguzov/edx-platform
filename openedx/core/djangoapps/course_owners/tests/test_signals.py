"""
Tests for signals resulting in CourseOwnership items creation
"""
import json
import unittest

from django.test.client import Client
from django.core.urlresolvers import reverse
from django.conf import settings

from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

from student.tests.factories import UserFactory

from openedx.core.djangoapps.course_owners.models import CourseOwnership


@unittest.skipUnless(settings.ROOT_URLCONF == 'cms.urls', 'Test only valid in cms')
class CreateOwnershipTest(ModuleStoreTestCase):
    """
    Test creation of CourseOwnership items on course creation and reruns
    """
    CREATE_USER = True

    def setUp(self):
        super(CreateOwnershipTest, self).setUp()
        self.client = Client()
        self.client.login(username=self.user.username, password=self.user_password)

    def tearDown(self):
        self.client.logout()
        ModuleStoreTestCase.tearDown(self)

    def test_new_course_ownership(self):
        """
        Test CourseOwner creation on course creation
        """
        response = self.client.post(
            reverse('course_handler'),
            data=json.dumps({
                'org': 'test_org',
                'course': 'test',
                'run': 'test_run',
                'display_name': 'Test Course'
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        course_id = CourseKey.from_string(data['course_key'])
        self.assertTrue(
            CourseOwnership.objects.filter(user=self.user, course_id=course_id).exists()
        )

    def test_rerun_ownership(self):
        course = CourseFactory.create()
        CourseOwnership.objects.create(course_id=course.id, user=self.user)

        response = self.client.post(
            reverse('course_handler'),
            data=json.dumps({
                'source_course_key': unicode(course.id),
                'org': course.org,
                'course': course.number,
                'run': 'new_run',
                'display_name': 'Test Course'
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        new_course_id = CourseKey.from_string(data['destination_course_key'])
        self.assertTrue(
            CourseOwnership.objects.filter(user=self.user, course_id=new_course_id).exists()
        )

    def test_rerun_multiple_ownership(self):
        """
        Test copying of all owners for the course rerun
        """
        course = CourseFactory.create()
        extra_owner = UserFactory()
        CourseOwnership.objects.create(course_id=course.id, user=self.user)
        CourseOwnership.objects.create(course_id=course.id, user=extra_owner)

        response = self.client.post(
            reverse('course_handler'),
            data=json.dumps({
                'source_course_key': unicode(course.id),
                'org': course.org,
                'course': course.number,
                'run': 'new_run',
                'display_name': 'Test Course'
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        new_course_id = CourseKey.from_string(data['destination_course_key'])
        self.assertTrue(
            CourseOwnership.objects.filter(user=self.user, course_id=new_course_id).exists()
            and CourseOwnership.objects.filter(user=extra_owner, course_id=new_course_id).exists()
        )
