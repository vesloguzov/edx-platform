# coding=utf-8

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
