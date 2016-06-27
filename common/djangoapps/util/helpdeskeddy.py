"""
API for creation of users and tickets in HelpDeskEddy service
"""
import json
import requests
import urlparse


HELPDESK_ENDPOINTS = {
    'list_users': {
        'path': '/api/v1/users/',
        'method': 'GET',
        'status_code': 200
    },
    'create_user': {
        'path': '/api/v1/users/',
        'method': 'POST',
        'status_code': 200
    },
    'create_ticket': {
        'path': '/api/v1/tickets/',
        'method': 'POST',
        'status_code': 200
    }
}


class HelpDeskEddyError(Exception):
    """Error indicating some unexpected HelpDeskEddy online API error"""
    pass


class HelpDeskEddyAPI(object):
    optional_user_fields = ('lastname', 'password', 'phone', 'website', 'skype')

    def __init__(self, url, api_key, depart_id=1):
        self.base_url = url
        self.api_key = api_key
        self.depart_id = depart_id
        self.request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_or_create_user(self, email, name, **kwargs):
        if not email or not name:
            raise HelpDeskEddyError('Email and name are required.')

        user_id = self._find_user_by_email(email)
        if user_id is None:
            user_id = self._create_user(email, name, **kwargs)
        return user_id

    def create_ticket(self, creator_id, subject, content):
        if not creator_id or not subject or not content:
            raise HelpDeskEddyError('Creator, subject and content are required.')

        ticket_create_url = urlparse.urljoin(self.base_url, HELPDESK_ENDPOINTS['create_ticket']['path'])
        ticket_data = {
            'notify': 1,
            'ticket': {
                'subject': subject,
                'content': content,
                'creator_id': creator_id,
                'depart_id': self.depart_id,
            }
        }

        ticket_create_response = requests.request(
            HELPDESK_ENDPOINTS['create_ticket']['method'],
            ticket_create_url,
            data=self._get_request_data(ticket_data),
            headers=self.request_headers
        )
        if ticket_create_response.status_code != HELPDESK_ENDPOINTS['create_ticket']['status_code']:
            raise HelpDeskEddyError('Unexpected HelpDeskEddy API response status on ticket creation: %s' % ticket_create_response.status)

        new_ticket_data = json.loads(ticket_create_response.content)
        if 'error' in new_ticket_data:
            raise HelpDeskEddyError(new_ticket_data['error'])
        if 'ticket_id' not in new_ticket_data:
            raise HelpDeskEddyError('ticket_id not received on ticket creation by HelpDeskEddy API')
        return new_ticket_data['ticket_id']

    def _get_request_data(self, data):
        request_data = {"apiKey": self.api_key}
        request_data.update(data)
        return json.dumps(request_data)

    def _find_user_by_email(self, email):
        user_search_url = urlparse.urljoin(self.base_url, HELPDESK_ENDPOINTS['list_users']['path'])

        user_search_response = requests.request(
            HELPDESK_ENDPOINTS['list_users']['method'],
            user_search_url,
            data=self._get_request_data({'filter': {'email': [email]}}),
            headers=self.request_headers
        )
        if user_search_response.status_code != HELPDESK_ENDPOINTS['list_users']['status_code']:
            raise HelpDeskEddyError('Unexpected HelpDeskEddy API response status on user search: %s' % user_search_response.status_code)
        if user_search_response.content == 'false':
            return None

        search_result = json.loads(user_search_response.content)
        if 'error' in search_result:
            raise HelpDeskEddyError(search_result['error'])

        return search_result.keys()[0]

    def _create_user(self, email, name, **kwargs):
        user_create_url = urlparse.urljoin(self.base_url, HELPDESK_ENDPOINTS['create_user']['path'])
        user_data = {'name': name, 'email': email}
        user_data.update({k: w for k,w in kwargs.items() if k in self.optional_user_fields})

        user_create_response = requests.request(
            HELPDESK_ENDPOINTS['create_user']['method'],
            user_create_url,
            data=self._get_request_data(user_data),
            headers=self.request_headers
        )
        if user_create_response.status_code != HELPDESK_ENDPOINTS['create_user']['status_code']:
            raise HelpDeskEddyError('Unexpected HelpDeskEddy API response status on user creation: %s' % user_create_response.status)

        new_user_data = json.loads(user_create_response.content)
        if 'error' in new_user_data:
            raise HelpDeskEddyError(new_user_data['error'])
        if 'user_id' not in new_user_data:
            raise HelpDeskEddyError('user_id not received on user creation by HelpDeskEddy API')
        return new_user_data['user_id']
