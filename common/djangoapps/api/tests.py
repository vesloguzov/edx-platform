"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from django.contrib.auth.models import User

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
