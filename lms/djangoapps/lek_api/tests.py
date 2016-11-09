# coding=utf-8
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import ddt
import json
import datetime
from unittest import skipIf, skipUnless, skip
from mock import patch
from uuid import uuid4
import urlparse

from django.test import TestCase
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.core import mail
from django.conf import settings

from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from opaque_keys.edx.locator import CourseLocator
from rest_framework import mixins

from student.models import CourseEnrollment
from certificates.models import GeneratedCertificate, CertificateStatuses
from student.tests.factories import UserFactory, CourseEnrollmentFactory
from instructor.enrollment import enroll_email

from serializers import UserSerializer
from views import UserViewSet

TEST_API_KEY = "test_api_key"

API_PROFILE_FIELDS = (
    'name',
    'nickname',
    'first_name',
    'last_name',
    'birthdate',
    'city',
)


class UserSerializerTest(TestCase):
    profile_fields = API_PROFILE_FIELDS

    def setUp(self):
        self.user = UserFactory.create(username='test', email='test@example.com')

    def test_serialization(self):
        serializer = UserSerializer(instance=self.user)
        data = serializer.data

        self.assertIn('uid', data)
        self.assertEquals(self.user.username, data['uid'])

        self.assertIn('email', data)
        self.assertEquals(self.user.email, data['email'])

        for field_name in self.profile_fields:
            self.assertIn(field_name, data)
            self.assertEquals(getattr(self.user.profile, field_name), data[field_name])

    def test_repetitive_user_not_valid(self):
        serializer = UserSerializer(data={'uid': self.user.username})
        self.assertFalse(serializer.is_valid(), 'Validation unexpectedly succeded')

    def test_create(self):
        data = {
            'uid': 'test1',
            'email': 'test1@example.com',
            'name': 'Test',
            'nickname': 'Nick',
            'first_name': 'FirstTest',
            'last_name': 'LastTest',
            'birthdate': datetime.date.today(),
            'city': 'Test city'
        }
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), 'Validation on creaion failed: %s' % serializer.errors)

        new_user = serializer.save()
        self.assertEquals(new_user.username, serializer.data['uid'])
        self.assertEquals(new_user.email, serializer.data['email'])
        for field_name in self.profile_fields:
            self.assertEquals(getattr(new_user.profile, field_name), data[field_name])

    def test_update(self):
        data = {
            'uid': self.user.username,
            'email': 'new_test@example.com',
            'name': 'New Test',
            'nickname': 'New Test',
            'first_name': 'Test name',
            'last_name': 'Test surname',
        }
        serializer = UserSerializer(self.user, data=data)
        self.assertTrue(serializer.is_valid(), 'Validation on update failed: %s' % serializer.errors)

        serializer.save()
        updated_user = User.objects.get(id=self.user.id)
        self.assertEquals(updated_user.username, data['uid'])
        self.assertEquals(updated_user.email, data['email'])
        self.assertEquals(updated_user.profile.name, data['name'])
        self.assertEquals(updated_user.profile.nickname, data['nickname'])
        self.assertEquals(updated_user.profile.first_name, data['first_name'])
        self.assertEquals(updated_user.profile.last_name, data['last_name'])

    def test_optional_fields(self):
        data = {'uid': 'test2', 'email': 'test2@example.com'}
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), 'Validation on update failed: %s' % serializer.errors)

    def test_required_fields(self):
        data = {}
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid(), 'Validation unexpectedly succeded')
        self.assertIn('uid', serializer.errors)

    def test_email_required_on_creation(self):
        data = {'uid': 'testx'}
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid(), 'Validation unexpectedly succeded')
        self.assertIn('email', serializer.errors)

    def test_partial_update(self):
        """
        Test that not required fields with defaults are not changed during partial update
        """
        data = {
            'uid': self.user.username,
            'nickname': 'New Test'
        }
        profile = self.user.profile
        profile.name = 'not-to-be-changed'
        profile.save()

        serializer = UserSerializer(self.user, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), 'Validation on update failed: %s' % serializer.errors)
        updated_user = serializer.save()
        self.assertEqual(updated_user.profile.nickname, data['nickname'])
        self.assertEqual(updated_user.profile.name, 'not-to-be-changed')

    def test_defaults_on_update(self):
        data = {
            'uid': self.user.username,
            'nickname': 'New Test'
        }
        profile = self.user.profile
        profile.name = 'to-be-removed'
        profile.save()

        serializer = UserSerializer(self.user, data=data)
        self.assertTrue(serializer.is_valid(), 'Validation on update failed: %s' % serializer.errors)
        updated_user = serializer.save()
        self.assertEqual(updated_user.profile.name, '')

    def test_invalid_on_duplicate_email(self):
        data = {
            'uid': self.user.username + '-new',
            'email': self.user.email,
        }
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid(), 'Validation unexpectedly succeded')

    def test_invalid_uid(self):
        data = {
            'uid': 'restricted+symbols in uid',
            'email': 'test@example.com',
        }
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid(), 'Validation unexpectedly succeded')
        self.assertIn('uid', serializer.errors)


@skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
@override_settings(EDX_API_KEY=TEST_API_KEY)
class APITest(SharedModuleStoreTestCase):
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
    profile_fields = API_PROFILE_FIELDS

    def setUp(self):
        super(UserViewSetTest, self).setUp()
        self.user = UserFactory.create(username='test', email='test@example.com')
        self.detail_url = reverse('profile-detail', kwargs={'username': self.user.username})
        self.list_url = reverse('profile-list')

    def tearDown(self):
        User.objects.all().delete()

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

    # @skip('Removed from framework upstream, may be fixed with mixin')
    def test_put_create(self):
        data = {
            'uid': '123',
            'email': 'test-other@example.com',
            'nickname': 'test',
            'name': 'Jonh Doe',
            'first_name': 'Jonh',
            'last_name': 'Doe',
            'birthdate': '2014-01-26',
            'city': 'Capital',
        }
        response = self._request_with_auth(
            'put', data=json.dumps(data),
            path=reverse('profile-detail', kwargs={'username': data['uid']}),
            content_type='application/json'
        )
        self.assertEquals(response.status_code, 201)

        user = User.objects.get(username=data['uid'])
        self.assertEqual(user.email, data['email'])

        for field_name in self.profile_fields:
            if field_name == 'birthdate':
                self.assertEqual(user.profile.birthdate, datetime.date(2014, 1, 26))
            else:
                self.assertEquals(getattr(user.profile, field_name), data[field_name])

    def test_put_update_optional_with_blank(self):
        """
        Test blank fields are updated correctly
        """
        data = {
            'uid': self.user.username,
            'email': self.user.email,
            'nickname': '',
            'name': '',
            'first_name': '',
            'last_name': '',
            'birthdate': None,
            'city': '',
        }
        response = self._request_with_auth(
            'put', data=json.dumps(data),
            path=reverse('profile-detail', kwargs={'username': data['uid']}),
            content_type='application/json'
        )
        self.assertEquals(response.status_code, 200)

        user = User.objects.get(username=self.user.username)
        self.assertEqual(user.email, self.user.email)
        self.assertEqual(user.profile.name, '')
        self.assertEqual(user.profile.first_name, '')
        self.assertEqual(user.profile.last_name, '')
        self.assertEqual(user.profile.birthdate, None)
        self.assertEqual(user.profile.city, '')

    def test_creation_fails_on_duplicate_email(self):
        data = {
            'uid': '123',
            'email': self.user.email
        }
        response = self._request_with_auth('post', data=data, path=reverse('profile-list'))
        self.assertEquals(response.status_code, 400)

    # TODO: test various variants of patch data
    def test_patch(self):
        """
        Test only fields that were patched are updated
        """
        data = {
            'uid': self.user.username,
            'name': 'New Name',
            'first_name': 'NewFirstName',
        }
        response = self._request_with_auth(
            'post', data=data,
            path=reverse('profile-detail', kwargs={'username': data['uid']}),
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH'
        )
        self.assertEquals(response.status_code, 200)

        user = User.objects.get(username=self.user.username)
        self.assertEqual(user.profile.name, data['name'])
        self.assertEqual(user.profile.first_name, data['first_name'])

        self.assertEqual(user.profile.last_name, self.user.profile.last_name)
        self.assertEqual(user.email, self.user.email)

    def test_enroll_pending(self):
        """
        Test enrollment of not-yet registered user
        """
        data = {
            'uid': 'new_test',
            'email': 'new_test@example.com',
        }
        course = CourseFactory.create()
        enroll_email(course.id, data['email'], auto_enroll=True)

        # create user and check enrollment
        self._request_with_auth('post', data=data, path=reverse('profile-list'))
        user = User.objects.get(username=data['uid'])
        self.assertTrue(CourseEnrollment.is_enrolled(user, course.id))

    def test_get_nonexistent_user(self):
        detail_url = reverse('profile-detail', kwargs={'username': 'nonexistent'})
        response = self._request_with_auth('get', detail_url)
        self.assertEqual(response.status_code, 404)


@ddt.ddt
class CourseViewSetTest(APITest):
    def test_list(self):
        course = CourseFactory.create()
        list_url = reverse('course-list')
        response = self._request_with_auth('get', list_url)
        self.assertEquals(response.status_code, 200)

    @ddt.data(ModuleStoreEnum.Type.mongo, ModuleStoreEnum.Type.split)
    def test_detail(self, modulestore_type):
        """
        Test course info is correctly fetched from any modulestore
        """
        with modulestore().default_store(modulestore_type):
            course = CourseFactory.create()
        detail_url = reverse('course-detail', kwargs={'course_id': unicode(course.id)})

        response = self._request_with_auth('get', detail_url)
        self.assertEquals(response.status_code, 200)

    def test_nonexistent_course(self):
        detail_url = reverse('course-detail', kwargs={'course_id': CourseLocator(org='no_org', course='no_course', run='1')})
        response = self._request_with_auth('get', detail_url)
        self.assertEquals(response.status_code, 404)


@ddt.ddt
class EnrollmentViewSetTest(APITest):
    def setUp(self):
        super(EnrollmentViewSetTest, self).setUp()
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
            'You have enrolled in {}'.format(self.course_other.display_name)
        )
        self.assertIn(
            reverse('course_root', kwargs={'course_id': self.course_other.id.to_deprecated_string()}),
            mail.outbox[0].body
        )

    @patch.dict('django.conf.settings.FEATURES', {'SEND_ENROLLMENT_EMAIL': True})
    @ddt.data((True, 0), (False, 1))
    @ddt.unpack
    def test_skip_enrollment_email(self, skip_enrollment_email, email_count):
        url = reverse('enrollment-enroll', kwargs={'user_username': self.user.username,
                                                   'course_id': self.course_other.id})
        response = self._request_with_auth(
            'post', url,
            data=json.dumps({'skip_enrollment_email': skip_enrollment_email}),
            content_type='application/json'
        )
        self.assertEquals(response.status_code, 200)
        self.assertEqual(len(mail.outbox), email_count)

    def test_enroll_error_if_enrolled(self):
        url = reverse('enrollment-enroll', kwargs={'user_username': self.user.username,
                                                   'course_id': self.course_enrolled.id})
        response = self._request_with_auth('post', url)
        self.assertEquals(response.status_code, 400)

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
            status=CertificateStatuses.downloadable,
            download_url='http://example.com/test'
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

    @patch.dict(settings.FEATURES, {'CERTIFICATES_HTML_VIEW': True})
    def test_html_certificate_url(self):
        """
        Test HTML certificate url is showed correctly
        """
        course = CourseFactory.create(number='with_html_certificate')
        course.cert_html_view_enabled = True
        course.save()
        self.store.update_item(course, self.user.id)

        CourseEnrollmentFactory.create(course_id=course.id, user=self.user)
        certificate = GeneratedCertificate.objects.create(
            course_id=course.id,
            user=self.user,
            status=CertificateStatuses.downloadable,
            verify_uuid=uuid4().hex
        )
        expected_certificate_url = reverse(
            'certificates:render_cert_by_uuid',
            kwargs=dict(certificate_uuid=certificate.verify_uuid)
        )

        url = reverse('enrollment-list', kwargs={'user_username': self.user.username})
        response = self._request_with_auth('get', url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)

        enrollment = filter(lambda item: item['course_id'] == unicode(course.id), data)[0]
        certificate_url = enrollment['certificate_url']
        self.assertNotEqual(urlparse.urlparse(certificate_url).scheme, '')  # check for absolute url
        self.assertTrue(certificate_url.endswith(expected_certificate_url),
                        "Unexpected certificate URL: %s" % enrollment['certificate_url'])

    def test_enroll_error_on_closed_enrollment(self):
        course_enrollment_closed = CourseFactory.create(number='closed_enrollment',
                                                        enrollment_end=datetime.datetime(1970, 1, 1))
        url = reverse('enrollment-enroll', kwargs={'user_username': self.user.username,
                                                   'course_id': course_enrollment_closed.id})
        response = self._request_with_auth('post', url)
        self.assertEquals(response.status_code, 400)

    @ddt.data('enrollment-enroll', 'enrollment-unenroll')
    def test_nonexistent_user(self, view_name):
        url = reverse(view_name, kwargs={
            'user_username': 'nonexistent_user',
            'course_id': self.course_enrolled.id
        })
        response = self._request_with_auth('post', url)
        self.assertEquals(response.status_code, 404)

    @ddt.data('enrollment-enroll', 'enrollment-unenroll')
    def test_nonexistent_course(self, view_name):
        url = reverse(view_name, kwargs={
            'user_username': self.user.username,
            'course_id': CourseLocator(org='no_org', course='no_course', run='1')
        })
        response = self._request_with_auth('post', url)
        self.assertEquals(response.status_code, 404)
