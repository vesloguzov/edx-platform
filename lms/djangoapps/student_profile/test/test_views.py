# -*- coding: utf-8 -*-
""" Tests for student profile views. """
from mock import patch

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.contrib.auth.models import AnonymousUser

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

from util.testing import UrlResetMixin
from student.tests.factories import UserFactory
from student.roles import CourseStaffRole
from openedx.core.djangoapps.course_owners.models import CourseOwnership
from openedx.core.djangoapps.user_api.preferences.api import set_user_preference
from openedx.core.djangoapps.user_api.accounts import ACCOUNT_VISIBILITY_PREF_KEY, PRIVATE_VISIBILITY

from student_profile.views import learner_profile_context


class LearnerProfileViewTest(UrlResetMixin, TestCase):
    """ Tests for the student profile view. """

    USERNAME = "username"
    PASSWORD = "password"
    CONTEXT_DATA = [
        'default_public_account_fields',
        'accounts_api_url',
        'preferences_api_url',
        'account_settings_page_url',
        'has_preferences_access',
        'own_profile',
        'country_options',
        'language_options',
        'account_settings_data',
        'preferences_data',
    ]

    def setUp(self):
        super(LearnerProfileViewTest, self).setUp()
        self.user = UserFactory.create(username=self.USERNAME, password=self.PASSWORD)
        self.client.login(username=self.USERNAME, password=self.PASSWORD)

    def test_context(self):
        """
        Verify learner profile page context data.
        """
        request = RequestFactory().get('/url')
        request.user = self.user

        context = learner_profile_context(request, self.USERNAME)

        self.assertEqual(
            context['data']['default_public_account_fields'],
            settings.ACCOUNT_VISIBILITY_CONFIGURATION['public_fields']
        )

        self.assertEqual(
            context['data']['accounts_api_url'],
            reverse("accounts_api", kwargs={'username': self.user.username})
        )

        self.assertEqual(
            context['data']['preferences_api_url'],
            reverse('preferences_api', kwargs={'username': self.user.username})
        )

        self.assertEqual(
            context['data']['profile_image_upload_url'],
            reverse("profile_image_upload", kwargs={'username': self.user.username})
        )

        self.assertEqual(
            context['data']['profile_image_remove_url'],
            reverse('profile_image_remove', kwargs={'username': self.user.username})
        )

        self.assertEqual(
            context['data']['profile_image_max_bytes'],
            settings.PROFILE_IMAGE_MAX_BYTES
        )

        self.assertEqual(
            context['data']['profile_image_min_bytes'],
            settings.PROFILE_IMAGE_MIN_BYTES
        )

        self.assertEqual(context['data']['account_settings_page_url'], reverse('account_settings'))

        for attribute in self.CONTEXT_DATA:
            self.assertIn(attribute, context['data'])

    def test_view(self):
        """
        Verify learner profile page view.
        """
        profile_path = reverse('learner_profile', kwargs={'username': self.USERNAME})
        response = self.client.get(path=profile_path)

        for attribute in self.CONTEXT_DATA:
            self.assertIn(attribute, response.content)

    def test_undefined_profile_page(self):
        """
        Verify that a 404 is returned for a non-existent profile page.
        """
        profile_path = reverse('learner_profile', kwargs={'username': "no_such_user"})
        response = self.client.get(path=profile_path)
        self.assertEqual(404, response.status_code)

    @patch.dict('django.conf.settings.FEATURES', {'ALLOW_PROFILE_ANONYMOUS_ACCESS': True})
    def test_anonymous_access_setting(self):
        """
        Verify that anonymous user can access profile page
        if settings.FEATURES['ALLOW_PROFILE_ANONYMOUS_ACCESS'] is set to True
        """
        self.client.logout()
        profile_path = reverse('learner_profile', kwargs={'username': self.USERNAME})
        response = self.client.get(path=profile_path)

        self.assertEqual(200, response.status_code)
        for attribute in self.CONTEXT_DATA:
            self.assertIn(attribute, response.content)


@override_settings(
    COURSE_CATALOG_VISIBILITY_PERMISSION='see_in_catalog',
    COURSE_LISTINGS={}
)
class CourseOwnerProfileViewTest(ModuleStoreTestCase):
    """Tests for profile view of users authoring any courses"""

    USERNAME = "username"
    PASSWORD = "password"

    def setUp(self):
        super(CourseOwnerProfileViewTest, self).setUp()
        self.user = UserFactory.create(username=self.USERNAME, password=self.PASSWORD)
        self.client.login(username=self.USERNAME, password=self.PASSWORD)

        self.course = CourseFactory.create(user_id=self.user.id, emit_signals=True)
        CourseOwnership.objects.create(course_id=self.course.id, user=self.user)

        self.hidden_course = CourseFactory.create(
            user_id=self.user.id,
            metadata={'catalog_visibility': 'about'},
            emit_signals=True
        )
        # suppose ordinary case when owner is a staff member of a course team
        CourseStaffRole(self.hidden_course.id).add_users(self.user)
        CourseOwnership.objects.create(course_id=self.hidden_course.id, user=self.user)

    def test_owned_courses(self):
        """Test owned courses are listed in context"""
        request = RequestFactory().get('/url')
        request.user = self.user
        context = learner_profile_context(request, self.USERNAME)

        self._assert_course_listing(self.course, context)
        self._assert_course_listing(self.hidden_course, context)  # because owner is automatically made course staff

    def test_owned_couses_for_anonymous_user(self):
        """Test owned course links access for anonymous user"""
        # more a so-called "learning" test for 'has_access' than a real test for profile page

        request = RequestFactory().get('/url')
        request.user = AnonymousUser()
        context = learner_profile_context(request, self.USERNAME)

        self._assert_course_listing(self.course, context)
        self._assert_course_listing(self.hidden_course, context, False)

    def test_owned_courses_empty_in_limited_profile(self):
        """
        Test owned courses are not listed at all in limited profile
        """
        set_user_preference(self.user, ACCOUNT_VISIBILITY_PREF_KEY, PRIVATE_VISIBILITY)

        request = RequestFactory().get('/url')
        request.user = self.user
        context = learner_profile_context(request, self.USERNAME)

        self._assert_course_listing(self.course, context, False)
        self._assert_course_listing(self.hidden_course, context, False)

    @override_settings(INDEX_PAGE_COURSE_LISTING=[])
    @patch.dict('django.conf.settings.FEATURES', {'ALWAYS_REDIRECT_HOMEPAGE_TO_DASHBOARD_FOR_AUTHENTICATED_USER': False})
    def test_owned_courses_with_course_listings(self):
        """
        Test owned courses are listed in context even if they are hidden
        on the main page
        """
        response = self.client.get(reverse('root'))
        self.assertNotContains(response, self.course.display_name)
        self.assertNotContains(response, self.hidden_course.display_name)

        request = RequestFactory().get('/url')
        request.user = self.user
        context = learner_profile_context(request, self.USERNAME)

        self._assert_course_listing(self.course, context)
        self._assert_course_listing(self.hidden_course, context)  # because owner is automatically made course staff

    def _assert_course_listing(self, course, context, listed=True):
        """
        Assert the course is present/absent in context
        """
        course_id = unicode(course.id)
        courses = context['data']['owned_courses_data']['owned_courses']
        return self.assertEqual(
            any(c['course_id'] == course_id for c in courses),
            listed
        )
