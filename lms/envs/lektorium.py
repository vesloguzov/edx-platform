# coding=utf-8

from path import path
_PROJECT_ROOT = path(__file__).abspath().dirname().dirname()
_REPO_ROOT = _PROJECT_ROOT.dirname()

# translations overriding default transifex messages
LOCALE_PATHS = (
    _REPO_ROOT + '/conf/lektorium_locale/',
    _REPO_ROOT + '/conf/locale/',
)
CERT_NAME_SHORT = u"сертификат"
CERT_NAME_LONG = u"сертификат"
CERT_URL = '/certificates/'
CERT_STORAGE_PATH = '/edx/var/edxapp/certificate_store/'
