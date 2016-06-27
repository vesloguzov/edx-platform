# -*- coding: utf-8 -*-
"""
Tests for HelpDeskEddy API and help backend
"""
import mock
import json
from collections import namedtuple

from django.test import TestCase

from util.helpdeskeddy import requests, HelpDeskEddyAPI, HelpDeskEddyError

MockResponse = namedtuple('MockResponse', ('status_code', 'content'))

API_KEY_ERROR_RESPONSE = json.dumps({"error": "No API Key provided"})
USER_EXISTS_RESPONSE = json.dumps({
    "321": {
        "user_id": "321",
        "name":"John",
        "lastname": "Doe",
        "phone": "",
        "skype": "",
        "email": "johndoe@example.com"
        }
})
USER_CREATED_RESPONSE = json.dumps({
    "user_id": "321",
    "password": "some_auto_password",
    "user_key": "some_auto_key"
})
USER_NOT_FOUND_RESPONSE = 'false'
TICKET_CREATED_RESPONSE = json.dumps({
    "ticket_id": "123",
    "unique_id": "some_unique_id"
})


class HelpDeskEddyAPITest(TestCase):
    def setUp(self):
        self.api = HelpDeskEddyAPI(url='http://dummy_url', api_key='dummy_api_key')

    def test_get_existing_user(self):
        with mock.patch.object(requests, 'request') as mock_request:
            mock_request.return_value = MockResponse(200, USER_EXISTS_RESPONSE)
            user_id = self.api.get_or_create_user(name='John', lastname='Doe', email='johndoe@example.com')
        self.assertEqual(user_id, '321')

    def test_create_user(self):
        with mock.patch.object(requests, 'request') as mock_request:
            mock_request.side_effect = [
                MockResponse(200, 'false'),
                MockResponse(200, USER_CREATED_RESPONSE),
            ]
            user_id = self.api.get_or_create_user(name='John', lastname='Doe', email='johndoe@example.com')
        self.assertEqual(user_id, '321')

    def test_get_or_create_user_empty_email(self):
        with self.assertRaises(HelpDeskEddyError) as e:
            user_id = self.api.get_or_create_user(name='John', lastname='Doe', email='')

    def test_create_user_empty_name(self):
        with self.assertRaises(HelpDeskEddyError) as e:
            user_id = self.api.get_or_create_user(name='', lastname='Doe', email='johndoe@example.com')

    def test_get_or_create_user_auth_error(self):
        """
        API should return HelpDeskEddyError when API key is rejected
        """
        with mock.patch.object(requests, 'request') as mock_request:
            mock_request.return_value = MockResponse(200, API_KEY_ERROR_RESPONSE)
            with self.assertRaises(HelpDeskEddyError) as e:
                user_id = self.api.get_or_create_user(name='John', lastname='Doe', email='johndoe@example.com')

    def test_create_ticket(self):
        with mock.patch.object(requests, 'request') as mock_request:
            mock_request.return_value = MockResponse(200, TICKET_CREATED_RESPONSE)
            ticket_id = self.api.create_ticket('1', u'test subject', u'test content')
        self.assertEqual(ticket_id, '123')

    def test_create_ticket_unicode(self):
        with mock.patch.object(requests, 'request') as mock_request:
            mock_request.return_value = MockResponse(200, TICKET_CREATED_RESPONSE)
            ticket_id = self.api.create_ticket('1', u'tёst subjёct', u'tёst contёnt')
        self.assertEqual(ticket_id, '123')

    def test_ticket_creation_auth_error(self):
        """
        API should return HelpDeskEddyError when API key is rejected
        """
        with mock.patch.object(requests, 'request') as mock_request:
            mock_request.return_value = MockResponse(200, API_KEY_ERROR_RESPONSE)
            with self.assertRaises(HelpDeskEddyError) as e:
                ticket_id = self.api.create_ticket('1', u'test subject', u'test content')
