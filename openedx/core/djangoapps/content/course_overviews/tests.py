"""
Tests for course_overviews app.
"""

import datetime
import ddt
import itertools

from django.utils import timezone

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore import ModuleStoreEnum

from certificates.api import get_active_web_certificate
from courseware.courses import course_image_url
from .models import CourseOverview

@ddt.ddt
class CourseOverviewTestCase(ModuleStoreTestCase):
    """
    Tests for CourseOverviewDescriptor model.
    """

    TODAY = timezone.now()
    YESTERDAY = TODAY - datetime.timedelta(days=1)
    TOMORROW = TODAY + datetime.timedelta(days=1)
    NEXT_MONTH = TODAY + datetime.timedelta(days=30)

    def check_course_overview_against_course(self, course):
        """Compares a CourseOverview object against its corresponding CourseDescriptor object

        Specifically, given a course, test that data within the following three
        objects match each other:
         - the CourseDescriptor itself
         - a CourseOverviewDescriptor that was newly constructed from _create_from_course
         - a CourseOverviewDescriptor that was loaded from the MySQL database
        """

        # Load the CourseOverview from the cache twice. The first load will be a cache miss (because the cache
        # is empty) so the course will be newly created with CourseOverviewDescriptor.create_from_course. The second
        # load will be a cache hit, so the course will be loaded from the cache.
        course_overview_cache_miss = CourseOverview.get_from_id(course.id)
        course_overview_cache_hit = CourseOverview.get_from_id(course.id)

        # Test if value of these attributes match between the three objects
        fields_to_test = [
            'id',
            'location',
            'display_name',
            'display_number_with_default',
            'display_org_with_default',
            'advertised_start',
            'facebook_url',
            'social_sharing_url',
            'certificates_display_behavior',
            'certificates_show_before_end',
            'cert_name_short',
            'cert_name_long',
            'lowest_passing_grade',
            'end_of_course_survey_url',
            'mobile_available',
            'visible_to_staff_only',
            'location',
            'number',
            'display_name_with_default',
            'start_date_is_still_default',
            'pre_requisite_courses'
        ]
        for attribute_name in fields_to_test:
            course_value = getattr(course, attribute_name)
            cache_miss_value = getattr(course_overview_cache_miss, attribute_name)
            cache_hit_value = getattr(course_overview_cache_hit, attribute_name)
            self.assertEqual(course_value, cache_miss_value)
            self.assertEqual(cache_miss_value, cache_hit_value)

        # Test if return values all methods are equal between the three objects
        methods_to_test = [
            'clean_id',
            'has_ended',
            'has_started',
            'start_datetime_text',
            'end_datetime_text',
            'may_certify',
        ]
        for method_name in methods_to_test:
            course_value = getattr(course, method_name)()
            cache_miss_value = getattr(course_overview_cache_miss, method_name)()
            cache_hit_value = getattr(course_overview_cache_hit, method_name)()
            self.assertEqual(course_value, cache_miss_value)
            self.assertEqual(cache_miss_value, cache_hit_value)

        # Other values to test
        others_to_test = [(
            course_image_url(course),
            course_overview_cache_miss.course_image_url,
            course_overview_cache_hit.course_image_url
        ), (
            get_active_web_certificate(course) is not None,
            course_overview_cache_miss.has_active_web_certificates,
            course_overview_cache_hit.has_active_web_certificates

        )]
        for (course_value, cache_miss_value, cache_hit_value) in others_to_test:
            self.assertEqual(course_value, cache_miss_value)
            self.assertEqual(cache_miss_value, cache_hit_value)

    @ddt.data(*itertools.product(
        [
            {
                "static_asset_path": "/my/cool/path",
                "display_name": "Test Course",
                "start": YESTERDAY,
                "end": TOMORROW,
                "pre_requisite_courses": ['course-v1://edX+test1+run1', 'course-v1://edX+test2+run1']
            },
            {}
        ],
        [ModuleStoreEnum.Type.mongo, ModuleStoreEnum.Type.split]
    ))
    @ddt.unpack
    def test_course_overview_behavior(self, course_kwargs, modulestore_type):
        """Tests if CourseOverviews and CourseDescriptors behave the same
        by comparing pairs of them given a variety of scenarios.

        Args:
            course_kwargs (dict): kwargs to be passed to course constructor
            modulestore_type (ModuleStoreEnum.Type)
            is_user_enrolled (bool)
        """

        course = CourseFactory.create(
            course="test_course",
            org="edX",
            default_store=modulestore_type,
            **course_kwargs
        )
        self.check_course_overview_against_course(course)
