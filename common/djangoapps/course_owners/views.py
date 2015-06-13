"""
Views related to course owners
"""
from django_future.csrf import ensure_csrf_cookie
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.conf import settings

from django_countries import countries

from microsite_configuration import microsite

from util.cache import cache_if_anonymous
from edxmako.shortcuts import render_to_response
from openedx.core.djangoapps.user_api.models import UserPreference
from openedx.core.djangoapps.user_api.accounts import ACCOUNT_VISIBILITY_PREF_KEY
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user

from .models import CourseOwnership


@ensure_csrf_cookie
@cache_if_anonymous()
@require_http_methods(['GET'])
def owners_list(request):
    """
    List all users owning the course(s)
    """
    owner_ids = CourseOwnership.objects.values_list('user', flat=True)
    owners = User.objects.filter(id__in=owner_ids).order_by('username')
    return render_to_response('owners.html', {'owners': owners})


@ensure_csrf_cookie
@cache_if_anonymous()
@require_http_methods(['GET'])
def owner_courses(request, username):
    owner = get_object_or_404(User, username=username)

    context = {
        'owner': owner,
        'courses': _get_owner_courses(request, owner),
        'profile': {
            'image': get_profile_image_urls_for_user(owner),
        },
    }
    if (UserPreference.get_value(owner, ACCOUNT_VISIBILITY_PREF_KEY) == 'all_users'
        and not owner.profile.requires_parental_consent()):
        context['profile'].update(_get_owner_profile(owner))

    return render_to_response('owner_courses.html', context)


def _get_owner_profile(user):
    profile = user.profile
    # TODO: should we translate language (since edX does not translate)?
    languages = [settings.LANGUAGE_DICT[lang.code]
                 for lang in profile.language_proficiencies.all()]
    return {
        'country': _(countries.name(profile.country)),
        'languages': languages,
        'bio': profile.bio,
    }


def _get_owner_courses(request, owner):
    from courseware.courses import get_courses, sort_by_announcement, sort_by_start_date

    courses = get_courses(request.user, request.META.get('HTTP_HOST'))

    owned_courses = [o.course_id for o in CourseOwnership.objects.filter(user=owner)]
    courses = [course for course in courses if course.id in owned_courses]

    if microsite.get_value("ENABLE_COURSE_SORTING_BY_START_DATE",
                           settings.FEATURES["ENABLE_COURSE_SORTING_BY_START_DATE"]):
        courses = sort_by_start_date(courses)
    else:
        courses = sort_by_announcement(courses)

    return courses
