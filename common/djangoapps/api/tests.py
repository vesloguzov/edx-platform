# coding=utf-8
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import json
import datetime
from unittest import skipIf
from mock import patch

from django.test import TestCase
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.core import mail

from xmodule.modulestore.tests.factories import CourseFactory
from rest_framework import mixins

from student.models import CourseEnrollment
from certificates.models import GeneratedCertificate, CertificateStatuses
from student.tests.factories import UserFactory, CourseEnrollmentFactory

from serializers import UserSerializer
from views import UserViewSet

TEST_API_KEY = "test_api_key"

class UserSerializerTest(TestCase):
    def setUp(self):
        self.user = UserFactory.create(username='test', email='test@example.com')

    def test_serialization(self):
        serializer = UserSerializer(instance=self.user)
        data = serializer.data

        self.assertIn('uid', data)
        self.assertEquals(self.user.username, data['uid'])

        self.assertIn('email', data)
        self.assertEquals(self.user.email, data['email'])

        self.assertIn('name', data)
        self.assertEquals(self.user.profile.name, data['name'])

        self.assertIn('nickname', data)
        self.assertEquals(self.user.profile.nickname, data['nickname'])

    def test_repetitive_user_not_valid(self):
        serializer = UserSerializer(data={'uid': self.user.username})
        self.assertFalse(serializer.is_valid())

    def test_create(self):
        data = {
            'uid': 'test1',
            'email': 'test1@example.com',
            'name': 'Test',
            'nickname': 'Nick'
        }
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        new_user = serializer.save()
        self.assertEquals(new_user.username, serializer.data['uid'])
        self.assertEquals(new_user.email, serializer.data['email'])
        self.assertEquals(new_user.profile.name, serializer.data['name'])
        self.assertEquals(new_user.profile.nickname, serializer.data['nickname'])

    def test_update(self):
        data = {
            'uid': self.user.username,
            'email': 'new_test@example.com',
            'name': 'New Test',
            'nickname': 'New Test'
        }
        serializer = UserSerializer(self.user, data=data)
        self.assertTrue(serializer.is_valid())

        serializer.save()
        updated_user = User.objects.get(id=self.user.id)
        self.assertEquals(updated_user.username, data['uid'])
        self.assertEquals(updated_user.email, data['email'])
        self.assertEquals(updated_user.profile.name, data['name'])
        self.assertEquals(updated_user.profile.nickname, data['nickname'])

    def test_optional_fields(self):
        data = {'uid': 'test2'}
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_required_fields(self):
        data = {}
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('uid', serializer.errors)


@override_settings(EDX_API_KEY=TEST_API_KEY)
class APITest(TestCase):
    @override_settings(EDX_API_KEY='')
    def test_empty_api_key_fail(self):
        if getattr(self, 'list_url', False):
            response = self.client.get(self.list_url)
            self.assertEquals(response.status_code, 403)

        if getattr(self, 'detail_url', False):
            response = self.client.get(self.detail_url)
            self.assertEquals(response.status_code, 403)

    @override_settings(DEBUG=True)
    @override_settings(EDX_API_KEY='')
    def test_empty_api_key_on_debug(self):
        if getattr(self, 'list_url', False):
            response = self.client.get(self.list_url)
            self.assertNotEquals(response.status_code, 403)

    def _request_with_auth(self, method, *args, **kwargs):
        """Issue a get request to the given URI with the API key header"""
        return getattr(self.client, method)(HTTP_X_EDX_API_KEY=TEST_API_KEY, *args, **kwargs)


class UserViewSetTest(APITest):
    def setUp(self):
        self.user = UserFactory.create(username='test', email='test@example.com')
        self.detail_url = reverse('user-detail', kwargs={'username': self.user.username})
        self.list_url = reverse('user-list')

    @override_settings(EDX_API_KEY='')
    def test_empty_api_key_fail(self):
        super(UserViewSetTest, self).test_empty_api_key_fail()

        response = self.client.post(self.list_url, {'uid': 'new_test'})
        self.assertEquals(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='new_test').exists())

    @skipIf(not issubclass(UserViewSet, mixins.ListModelMixin), 'User list api disabled')
    def test_list(self):
        response = self._request_with_auth('get', self.list_url)
        self.assertEquals(response.status_code, 200)

    def test_create_incorrect_username(self):
        incorrect_uids = ['a b', 'a+b', 'a@b', u'ша']
        for uid in incorrect_uids:
            data = {'uid': uid}
            response = self._request_with_auth('post', self.list_url, data)
            self.assertEqual(response.status_code, 400)

    def test_put_create(self):
        data = {
            'uid': '123',
            'email': 'test-other@example.com',
            'nickname': 'test',
            'name': 'Jonh Doe',
        }
        response = self._request_with_auth('put', data=data,
                    path=reverse('user-detail', kwargs={'username': data['uid']}))
        self.assertEquals(response.status_code, 201)

        user = User.objects.get(username=data['uid'])
        self.assertEquals(user.email, data['email'])
        self.assertEquals(user.profile.nickname, data['nickname'])
        self.assertEquals(user.profile.name, data['name'])


class CourseViewSetTest(APITest):
    def setUp(self):
        self.course = CourseFactory.create()
        self.list_url = reverse('course-list')
        self.detail_url = reverse('course-detail', kwargs={'course_id': self.course.id.to_deprecated_string()})

    def test_list(self):
        response = self._request_with_auth('get', self.list_url)
        self.assertEquals(response.status_code, 200)

    def test_detail(self):
        response = self._request_with_auth('get', self.detail_url)
        self.assertEquals(response.status_code, 200)


class EnrollmentViewSetTest(APITest):
    def setUp(self):
        self.user = UserFactory.create(username='test', email='test@example.com')

        self.course_enrolled = CourseFactory.create(number='enrolled')
        CourseEnrollmentFactory.create(course_id=self.course_enrolled.id, user=self.user)

        self.course_other = CourseFactory.create(number='other')

    def tearDown(self):
        User.objects.all().delete()

    def test_list(self):
        url = reverse('enrollment-list', kwargs={'user_username': self.user.username})
        response = self._request_with_auth('get', url)

        self.assertIn(self.course_enrolled.id.to_deprecated_string(), response.content)
        self.assertNotIn(self.course_other.id.to_deprecated_string(), response.content)

    def test_enroll(self):
        url = reverse('enrollment-enroll', kwargs={'user_username': self.user.username,
                                                   'course_id': self.course_other.id})
        response = self._request_with_auth('post', url)

        self.assertEquals(response.status_code, 200)
        self.assertTrue(CourseEnrollment.is_enrolled(self.user, self.course_other.id))

    @patch.dict('django.conf.settings.FEATURES', {'SEND_ENROLLMENT_EMAIL': True})
    def test_enrollment_email(self):
        url = reverse('enrollment-enroll', kwargs={'user_username': self.user.username,
                                                   'course_id': self.course_other.id})
        response = self._request_with_auth('post', url)
        self.assertEquals(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'You have enrolled in Robot Super Course'
        )
        self.assertIn(
            reverse('course_root', kwargs={'course_id': self.course_other.id.to_deprecated_string()}),
            mail.outbox[0].body
        )

    def test_enroll_error_if_enrolled(self):
        url = reverse('enrollment-enroll', kwargs={'user_username': self.user.username,
                                                   'course_id': self.course_enrolled.id})
        response = self._request_with_auth('post', url)
        self.assertEquals(response.status_code, 400)

    # TODO: test enrollment to courses with different modes

    def test_unenroll(self):
        url = reverse('enrollment-unenroll', kwargs={'user_username': self.user.username,
                                                   'course_id': self.course_enrolled.id})
        response = self._request_with_auth('post', url)

        self.assertEquals(response.status_code, 204)
        self.assertFalse(CourseEnrollment.is_enrolled(self.user, self.course_enrolled.id))

    def test_unenroll_error_if_not_enrolled(self):
        url = reverse('enrollment-unenroll', kwargs={'user_username': self.user.username,
                                                   'course_id': self.course_other.id})
        response = self._request_with_auth('post', url)
        self.assertEquals(response.status_code, 400)

    def test_certificate(self):
        """Test certificates are showed for corresponding courses"""
        course_with_certificate = CourseFactory.create(number='with_certificate')
        CourseEnrollmentFactory.create(course_id=course_with_certificate.id, user=self.user)

        certificate = GeneratedCertificate.objects.create(
                       course_id=course_with_certificate.id,
                       user=self.user,
                       status = CertificateStatuses.downloadable,
                       download_url = 'http://example.com/test'
        )

        url = reverse('enrollment-list', kwargs={'user_username': self.user.username})
        response = self._request_with_auth('get', url)

        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        for item in data:
            if item['course_id'] == self.course_enrolled.id.to_deprecated_string():
                self.assertIsNone(item['certificate_url'])
            elif item['course_id'] == course_with_certificate.id.to_deprecated_string():
                self.assertEquals(item['certificate_url'], certificate.download_url)

    def test_enroll_error_on_closed_enrollment(self):
        course_enrollment_closed = CourseFactory.create(number='closed_enrollment',
                                                        enrollment_end=datetime.datetime(1970, 1, 1))
        url = reverse('enrollment-enroll', kwargs={'user_username': self.user.username,
                                                   'course_id': course_enrollment_closed.id})
        response = self._request_with_auth('post', url)
        self.assertEquals(response.status_code, 400)
