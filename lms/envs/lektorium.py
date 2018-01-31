# coding=utf-8
import datetime

CERT_NAME_SHORT = u"сертификат"
CERT_NAME_LONG = u"сертификат"
CERT_URL = 'certificates/'
CERT_STORAGE_PATH = '/edx/var/edxapp/certificates/'

CAS_VERSION = '3'
CAS_USER_CREATOR = 'external_auth.views.cas_create_user'
CAS_ATTRIBUTE_KEYS = {
    'email': 'mail',
    'name': 'name',
    'nickname': 'nickname',
    'day_of_birth': 'birthday',
    'gender': 'gender',
    # 'language': 'language',
    # 'level_of_education',
}
CAS_INSTANT_LOGIN_EXEMPT = (
    'lek_api.',
)

USER_DATA_REQUEST_TIMEOUT = datetime.timedelta(hours=24)
SYNC_USER_URL = 'https://www.lektorium.tv/uidname/node/25618?api-key={}'

# Custom formats used on platform and default values for them
FORMAT_MODULE_PATH = [
    'conf.locale',
]
CERTIFICATE_DATE_FORMAT = 'F j, Y'

# disable broken feature explicitly
ENABLE_ENTERPRISE_INTEGRATION = False
