# coding=utf-8
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import ddt
import json
import datetime
from unittest import skipIf
from mock import patch
from uuid import uuid4
import urlparse

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core import mail
from django.conf import settings
from django.test.utils import override_settings

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
from course_modes.tests.factories import CourseModeFactory

from lek_api.views import UserViewSet


TEST_API_KEY = "test_api_key"

API_PROFILE_FIELDS = (
    'name',
    'nickname',
    'first_name',
    'last_name',
    'birthdate',
    'city',
)



@override_settings(EDX_API_KEY=TEST_API_KEY)
class APITest(SharedModuleStoreTestCase):
    @override_settings(EDX_API_KEY='')
    def test_empty_api_key_fail(self):
        if getattr(self, 'list_url', False):
            response = self.client.get(self.list_url)
            self.assertEqual(response.status_code, 403)

        if getattr(self, 'detail_url', False):
            response = self.client.get(self.detail_url)
            self.assertEqual(response.status_code, 403)

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
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='new_test').exists())

    @skipIf(not issubclass(UserViewSet, mixins.ListModelMixin), 'User list api disabled')
    def test_list(self):
        response = self._request_with_auth('get', self.list_url)
        self.assertEqual(response.status_code, 200)

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
            'first_name': 'Jonh',
            'last_name': 'Doe',
            'birthdate': '2014-01-26',
            'city': 'Capital',
            'gender': 'm'
        }
        response = self._request_with_auth(
            'put', data=json.dumps(data),
            path=reverse('profile-detail', kwargs={'username': data['uid']}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)

        user = User.objects.get(username=data['uid'])
        self.assertEqual(user.email, data['email'])

        for field_name in self.profile_fields:
            if field_name == 'birthdate':
                self.assertEqual(user.profile.birthdate, datetime.date(2014, 1, 26))
            else:
                self.assertEqual(getattr(user.profile, field_name), data[field_name])

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
            'gender': None
        }
        response = self._request_with_auth(
            'put', data=json.dumps(data),
            path=reverse('profile-detail', kwargs={'username': data['uid']}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username=self.user.username)
        self.assertEqual(user.email, self.user.email)
        self.assertEqual(user.profile.name, '')
        self.assertEqual(user.profile.first_name, '')
        self.assertEqual(user.profile.last_name, '')
        self.assertEqual(user.profile.birthdate, None)
        self.assertEqual(user.profile.city, '')
        self.assertEqual(user.profile.gender, None)

    def test_creation_fails_on_duplicate_email(self):
        data = {
            'uid': '123',
            'email': self.user.email
        }
        response = self._request_with_auth('post', data=data, path=reverse('profile-list'))
        self.assertEqual(response.status_code, 400)

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
        self.assertEqual(response.status_code, 200)

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

    def test_put_no_update_on_invalid_gender(self):
        """
        Test no put on invalid gender
        """
        data = {
            'uid': self.user.username,
            'email': self.user.email,
            'gender': 'INVALID'
        }
        response = self._request_with_auth(
            'put', data=json.dumps(data),
            path=reverse('profile-detail', kwargs={'username': data['uid']}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        error_data = json.loads(response.content)
        self.assertIn('gender', error_data)
        self.assertIn('not a valid choice', error_data['gender'][0])
        self.assertNotEqual(self.user.profile.gender, data['gender'])


@ddt.ddt
class CourseViewSetTest(APITest):
    def test_list(self):
        course = CourseFactory.create()
        list_url = reverse('course-list')
        response = self._request_with_auth('get', list_url)
        self.assertEqual(response.status_code, 200)

    @ddt.data(ModuleStoreEnum.Type.mongo, ModuleStoreEnum.Type.split)
    def test_detail(self, modulestore_type):
        """
        Test course info is correctly fetched from any modulestore
        """
        with modulestore().default_store(modulestore_type):
            course = CourseFactory.create()
        detail_url = reverse('course-detail', kwargs={'course_id': unicode(course.id)})

        response = self._request_with_auth('get', detail_url)
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_course(self):
        detail_url = reverse('course-detail', kwargs={'course_id': CourseLocator(org='no_org', course='no_course', run='1')})
        response = self._request_with_auth('get', detail_url)
        self.assertEqual(response.status_code, 404)


@ddt.ddt
class EnrollmentViewSetTest(APITest):
    def setUp(self):
        super(EnrollmentViewSetTest, self).setUp()
        self.user = UserFactory.create(username='test', email='test@example.com')

        self.course_enrolled = CourseFactory.create(number='enrolled')
        CourseEnrollmentFactory.create(course_id=self.course_enrolled.id, user=self.user)
        CourseModeFactory.create(mode_slug='honor', course_id=self.course_enrolled.id)
        CourseModeFactory.create(mode_slug='professional', course_id=self.course_enrolled.id)

        self.course_other = CourseFactory.create(number='other')

    def tearDown(self):
        User.objects.all().delete()

    def test_list(self):
        url = reverse('enrollment-list', kwargs={'user_username': self.user.username})
        response = self._request_with_auth('get', url)

        self.assertIn(self.course_enrolled.id.to_deprecated_string(), response.content)
        self.assertNotIn(self.course_other.id.to_deprecated_string(), response.content)

    def test_enroll_with_default_mode(self):
        response = self._enroll(self.user, self.course_other.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CourseEnrollment.is_enrolled(self.user, self.course_other.id))

    @patch.dict('django.conf.settings.FEATURES', {'SEND_ENROLLMENT_EMAIL': True})
    def test_enrollment_email(self):
        response = self._enroll(self.user, self.course_other.id)
        self.assertEqual(response.status_code, 200)

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
        response = self._enroll(self.user, self.course_other.id, {'skip_enrollment_email': skip_enrollment_email})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), email_count)

    @ddt.data('honor', 'audit', 'verified', 'professional', 'no-id-professional', 'credit')
    def test_enrollment_mode(self, mode):
        response = self._enroll(self.user, self.course_other.id, {'mode': mode})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CourseEnrollment.enrollment_mode_for_user(self.user, self.course_other.id),
                         (mode, True))

    def test_invalid_enrollment_mode(self):
        response = self._enroll(self.user, self.course_other.id, {'mode': 'invalid'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid course mode', response.content)

    @ddt.data('honor', 'audit', 'verified', 'professional', 'no-id-professional', 'credit')
    def test_update_enrollment_mode(self, mode):
        response = self._enroll(self.user, self.course_enrolled.id, {'mode': mode})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CourseEnrollment.enrollment_mode_for_user(self.user, self.course_enrolled.id),
                         (mode, True))

    def test_enroll_error_on_closed_enrollment(self):
        course_enrollment_closed = CourseFactory.create(number='closed_enrollment',
                                                        enrollment_end=datetime.datetime(1970, 1, 1))
        response = self._enroll(self.user, course_enrollment_closed.id)
        self.assertEqual(response.status_code, 400)

    def test_unenroll(self):
        url = reverse('enrollment-unenroll', kwargs={'user_username': self.user.username,
                                                     'course_id': self.course_enrolled.id})
        response = self._request_with_auth('post', url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(CourseEnrollment.is_enrolled(self.user, self.course_enrolled.id))

    def test_unenroll_error_if_not_enrolled(self):
        url = reverse('enrollment-unenroll', kwargs={'user_username': self.user.username,
                                                     'course_id': self.course_other.id})
        response = self._request_with_auth('post', url)
        self.assertEqual(response.status_code, 400)

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

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        for item in data:
            if item['course_id'] == self.course_enrolled.id.to_deprecated_string():
                self.assertIsNone(item['certificate_url'])
            elif item['course_id'] == course_with_certificate.id.to_deprecated_string():
                self.assertEqual(item['certificate_url'], certificate.download_url)

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
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        enrollment = filter(lambda item: item['course_id'] == unicode(course.id), data)[0]
        certificate_url = enrollment['certificate_url']
        self.assertNotEqual(urlparse.urlparse(certificate_url).scheme, '')  # check for absolute url
        self.assertTrue(certificate_url.endswith(expected_certificate_url),
                        "Unexpected certificate URL: %s" % enrollment['certificate_url'])

    @ddt.data('enrollment-enroll', 'enrollment-unenroll')
    def test_nonexistent_user(self, view_name):
        url = reverse(view_name, kwargs={
            'user_username': 'nonexistent_user',
            'course_id': self.course_enrolled.id
        })
        response = self._request_with_auth('post', url)
        self.assertEqual(response.status_code, 404)

    @ddt.data('enrollment-enroll', 'enrollment-unenroll')
    def test_nonexistent_course(self, view_name):
        url = reverse(view_name, kwargs={
            'user_username': self.user.username,
            'course_id': CourseLocator(org='no_org', course='no_course', run='1')
        })
        response = self._request_with_auth('post', url)
        self.assertEqual(response.status_code, 404)

    def _enroll(self, user, course_id, data=None):
        url = reverse('enrollment-enroll', kwargs={'user_username': user.username, 'course_id': course_id})
        if data:
            return self._request_with_auth(
                'post', url,
                data=json.dumps(data),
                content_type='application/json'
            )
        else:
            return self._request_with_auth('post', url)
