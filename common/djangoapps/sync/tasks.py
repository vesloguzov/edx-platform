import json
import  urllib

import requests

from django.conf import settings

from celery import task
from celery.utils.log import get_task_logger


# TODO: task retry
# TODO: task queue

log = get_task_logger(__name__)

@task
def sync_user_profile(username):
    url = getattr(settings, 'SYNC_USER_URL', None)
    if not url:
        log.error('Missing sync url')
    #url = url.format(urllib.quote(user.username))
    #headers = {'x-http-api-key': settings.EDX_API_KEY}

    url = url.format(urllib.quote(settings.EDX_API_KEY))
    headers = {'Content-Type': 'application/json'}
    payload = {
        'type': 'edx_users',
        'title': username,
        'body': {'und': {"0": {'value': "I cannot hate you, but you owe me a cake"}}},
    }
    print url
    print payload

    try:
        # response = requests.put(url, headers=headers)
        response = requests.put(url, data=json.dumps(payload), headers=headers)
    except requests.exceptions.RequestException as e:
        log.error(e.message)
        raise
    else:
        if response.status_code == requests.codes.ok:
            log.info('Successfully sent user update signal')
        else:
            log.error('Sync: unexpected server response: {} {}'.format(response.status_code, response.text))
