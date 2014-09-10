"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.core.urlresolvers import reverse

from student.tests.factories import UserFactory
from serializers import UserSerializer


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

    def test_repetitive_user_not_valid(self):
        serializer = UserSerializer(data={'uid': self.user.username})
        self.assertFalse(serializer.is_valid())

    def test_create(self):
        data = {'uid': 'test1', 'email': 'test1@example.com', 'name': 'Test'}
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        new_user = serializer.save()
        self.assertEquals(new_user.username, serializer.data['uid'])
        self.assertEquals(new_user.email, serializer.data['email'])
        self.assertEquals(new_user.profile.name, serializer.data['name'])

    def test_update(self):
        data = {'uid': self.user.username, 'email': 'new_test@example.com', 'name': 'New Test'}
        serializer = UserSerializer(self.user, data=data)
        self.assertTrue(serializer.is_valid())

        serializer.save()
        updated_user = User.objects.get(id=self.user.id)
        self.assertEquals(updated_user.username, data['uid'])
        self.assertEquals(updated_user.email, data['email'])
        self.assertEquals(updated_user.profile.name, data['name'])

    def test_optional_fields(self):
        data = {'uid': 'test2'}
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid())


TEST_API_KEY = "test_api_key"

@override_settings(EDX_API_KEY=TEST_API_KEY)
class UserViewSetTest(TestCase):
    def setUp(self):
        self.user = UserFactory.create(username='test', email='test@example.com')
        self.detail_url = reverse('user-detail', kwargs={'username': self.user.username})

        self.list_url = reverse('user-list')

    @override_settings(EDX_API_KEY='')
    def test_empty_api_key_fail(self):
        response = self.client.get(self.list_url)
        self.assertEquals(response.status_code, 403)

        response = self.client.get(self.detail_url)
        self.assertEquals(response.status_code, 403)

        response = self.client.post(self.list_url, {'uid': 'new_test'})
        self.assertEquals(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='new_test').exists())

    @override_settings(DEBUG=True)
    @override_settings(EDX_API_KEY='')
    def test_empty_api_key_on_debug(self):
        response = self.client.get(self.list_url)
        self.assertEquals(response.status_code, 200)

    def test_list(self):
        response = self._request_with_auth('get', self.list_url)
        self.assertEquals(response.status_code, 200)

    def _request_with_auth(self, method, *args, **kwargs):
        """Issue a get request to the given URI with the API key header"""
        return getattr(self.client, method)(HTTP_X_EDX_API_KEY=TEST_API_KEY, *args, **kwargs)
