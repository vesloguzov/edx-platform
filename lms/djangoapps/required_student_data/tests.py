"""
Tests for required student data form
"""
import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from xmodule.modulestore.tests.factories import CourseFactory

from student.tests.factories import UserFactory, UserProfileFactory

class RequiredStudentDataTest(TestCase):
    """
    Tests for required student data form
    """
    @classmethod
    def setUpClass(cls):
        cls.course = CourseFactory.create()
        cls.postpone_url = reverse('postpone_required_data_update')
        cls.update_url = reverse('update_required_data')
        cls.data = {
            'first_name': 'test',
            'last_name': 'test',
            'birthdate': '2014-07-28',
        }

    def setUp(self):
        self.user = UserFactory.create(password='test')
        profile = UserProfileFactory.create(
            user=self.user,
            first_name='',
            last_name='',
            birthdate=None
        )
        self.client = Client()
        self.client.login(username=self.user.username, password='test')

    def tearDown(self):
        self.client.logout()
        User.objects.all().delete()

    def test_form_rendered(self):
        '''Test whether form appears for user having no required information'''
        self.assertTrue(self._form_appears())

    def test_postpone(self):
        '''Test whether form does not appear after postpone action'''
        self.client.post(self.postpone_url)
        self.assertFalse(self._form_appears())

    def test_postpone_awake(self):
        '''Test whether form appears again after postpone period'''
        # TODO
        pass

    def test_update_all_required_fields(self):
        '''Test whether form does not appear after complete update action'''
        self.client.post(self.update_url, self.data)
        self.assertFalse(self._form_appears())

    def test_updated_fields(self):
        '''Test form fields are saved correctly'''
        self.client.post(self.update_url, self.data)
        profile = self.user.profile
        self.assertEqual(profile.first_name, self.data['first_name'])
        self.assertEqual(profile.last_name, self.data['last_name'])
        self.assertEqual(
            profile.birthdate and profile.birthdate.strftime('%Y-%m-%d'),
            self.data['birthdate']
        )

    def test_skip_last_name(self):
        pass

    def test_invalid_birthdate(self):
        '''Test wheter response with errors list is returned on invalid birthdate'''
        data = self.data.copy()
        data['birthdate'] = 'invalid'
        response = self.client.post(self.update_url, data)
        self.assertEqual(response.status_code, 400)

        self.assertIn('errors', response.content)
        self.assertIn('birthdate', response.content)

    def test_partial_update_postponed(self):
        pass

    def test_course_staff_skipped(self):
        pass

    def test_global_staff_skipped(self):
        # self.user.is
        pass

    def test_invalid_course_key(self):
        pass

    def _form_appears(self):
        url = reverse('info', args=[self.course.id.to_deprecated_string()])
        response = self.client.get(url)
        return 'required_student_data_form' in response.content
