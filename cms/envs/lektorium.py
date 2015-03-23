# coding=utf-8

from path import path
_PROJECT_ROOT = path(__file__).abspath().dirname().dirname()
_REPO_ROOT = _PROJECT_ROOT.dirname()

# translations overriding default transifex messages
LOCALE_PATHS = (
    _REPO_ROOT + '/conf/lektorium_locale/',
    _REPO_ROOT + '/conf/locale/',
)

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
    'api.',
)

COURSE_UPDATE_DATE_FORMAT = 'dd mm yy'
