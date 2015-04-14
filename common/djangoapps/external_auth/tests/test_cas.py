"""
Unit test for cas-specific authentication details
"""
from unittest import skip

from django.test.utils import override_settings
from django.contrib.auth.models import User
from django.db import IntegrityError

from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from student.tests.factories import UserFactory
from student.models import UserProfile, CourseEnrollment
from external_auth.views import cas_create_user
from instructor.enrollment import enroll_email

class CASUserCreatorTest(ModuleStoreTestCase):
    def setUp(self):
        super(CASUserCreatorTest, self).setUp()
        self.username =  'test'
        self.attrs = {'mail': 'test@example.com'}

    def test_create_simple(self):
        cas_create_user(self.username, self.attrs)

        self.assertTrue(
            User.objects.filter(username=self.username, email=self.attrs['mail']).exists()
        )

    @skip('Until user model with unique email restriction')
    def test_repetitive_email(self):
        existing_user = UserFactory.create(email=self.attrs['mail'])
        # TODO: fix when handling this IntegrityError or special exception in cas
        with self.assertRaises(IntegrityError):
            cas_create_user(self.username, self.attrs)


    def test_profile_creation(self):
        attrs = {
            'mail': 'test@example.com',
            'name': 'Test User',
            'nickname': 'Test Nick',
        }
        self.assertFalse(User.objects.filter(email=attrs['mail']).exists())
        cas_create_user(self.username, attrs)

        user = User.objects.get(username=self.username)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        profile = user.profile
        self.assertEqual(profile.name, attrs['name'])
        self.assertEqual(profile.nickname, attrs['nickname'])

    def test_enroll_pending(self):
        course = CourseFactory.create()
        self.assertFalse(User.objects.filter(email=self.attrs['mail']).exists())
        enroll_email(course.id, self.attrs['mail'], auto_enroll=True)

        cas_create_user(self.username, self.attrs)
        user = User.objects.get(username=self.username)
        self.assertTrue(CourseEnrollment.is_enrolled(user, course.id))
