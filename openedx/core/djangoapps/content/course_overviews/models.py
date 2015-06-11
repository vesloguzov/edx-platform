"""
Declaration of CourseOverview model
"""

from datetime import datetime as date_time  # the as clause avoids naming conflicts the DateTime field
import json
from util.date_utils import strftime_localized

import django.db.models
from django.db.models.fields import *
from django.utils.timezone import UTC
from django.utils.translation import ugettext

from certificates.api import get_active_web_certificate
from xmodule import course_metadata_utils
from courseware.courses import course_image_url
from xmodule.modulestore.django import modulestore
from xmodule_django.models import CourseKeyField, UsageKeyField

class CourseOverview(django.db.models.Model):
    """Model for storing and caching basic information about a course.

    This model contains basic course metadata such as an ID, display name,
    image URL, and any other information that would be necessary display
    a course as part of a user dashboard or enrollment API.
    """

    # Course identification
    id = CourseKeyField(db_index=True, primary_key=True, max_length=255)
    _location = UsageKeyField(max_length=255)
    display_name = TextField(null=True)
    display_number_with_default = TextField()
    display_org_with_default = TextField()

    # Start/end dates
    start = DateTimeField(null=True)
    end = DateTimeField(null=True)
    advertised_start = TextField(null=True)

    # URLs
    course_image_url = TextField()
    facebook_url = TextField(null=True)
    social_sharing_url = TextField(null=True)

    # Certification data
    certificates_display_behavior = TextField(null=True)
    certificates_show_before_end = BooleanField()
    has_active_web_certificates = BooleanField()
    cert_name_short = TextField()
    cert_name_long = TextField()
    lowest_passing_grade = DecimalField(max_digits=5, decimal_places=2)
    end_of_course_survey_url = TextField(null=True)

    # Access parameters
    mobile_available = BooleanField()
    visible_to_staff_only = BooleanField()
    _pre_requisite_courses_json = TextField()  # JSON representation of list of CourseKey strings

    @staticmethod
    def _create_from_course(course):
        """Creates a CourseOverview object out of a CourseDescriptor.

        Does not touch the database, simply constructs and returns an overview
        from the given course.

        Args:s
            course (CourseDescriptor): any course descriptor object

        Returns:
            CourseOverview: overview extracted from the given course
        """
        return CourseOverview(
            id=course.id,
            _location=course.location,
            display_name=course.display_name,
            display_number_with_default=course.display_number_with_default,
            display_org_with_default=course.display_org_with_default,

            start=course.start,
            end=course.end,
            advertised_start=course.advertised_start,

            course_image_url=course_image_url(course),
            facebook_url=course.facebook_url,
            social_sharing_url=course.social_sharing_url,

            certificates_display_behavior=course.certificates_display_behavior,
            certificates_show_before_end=course.certificates_show_before_end,
            has_active_web_certificates=(get_active_web_certificate(course) is not None),
            cert_name_short=course.cert_name_short,
            cert_name_long=course.cert_name_long,
            lowest_passing_grade=course.lowest_passing_grade,
            end_of_course_survey_url=course.end_of_course_survey_url,

            mobile_available=course.mobile_available,
            visible_to_staff_only=course.visible_to_staff_only,
            _pre_requisite_courses_json=json.dumps(course.pre_requisite_courses)
        )

    @staticmethod
    def get_from_id(course_id):
        """Load a CourseOverview object for a given course ID.

        First, we try to load the CourseOverview from the database. If it
        doesn't exist, we load the entire course from modulestore, create a
        CourseOverview object from it, and then cache it in the database for
        future use.

        Args:
            course_id (CourseKey): the ID of the course overview to be loaded

        Returns:
            CourseOverview: overview of the requested course
        """
        course_overview = None
        try:
            course_overview = CourseOverview.objects.get(id=course_id)
            # Cache hit! Just return the overview
        except CourseOverview.DoesNotExist:
            # Cache miss. Load entire course and create a CourseOverview from it
            course = modulestore().get_course(course_id)
            if course:
                course_overview = CourseOverview._create_from_course(course)
                course_overview.save()  # Save new overview to the cache
        return course_overview

    def __repr__(self):
        """
        Returns a simple string representation of this object for debugging.

        Example return value: CourseOverview(location=course-v1://edX+DemoX.1+2014)
        """
        return "{}(location={})".format(self.__class__.__name__, self.location)

    def __str__(self):
        """
        Returns a string representation of this object suitable for a user to see.
        """
        return unicode(self.id)

    def clean_id(self, padding_char='='):
        """
        Returns a unique deterministic base32-encoded ID for the course.

        Args
            padding_char (str): Character used for padding at end of base-32
                                -encoded string, defaulting to '='
        """
        return course_metadata_utils.clean_id(self.location, padding_char)

    @property
    def location(self):
        """Returns the UsageKey of this course.

        UsageKeyField has a strange behavior where it fails to parse the "run"
        of a course out of the serialized form of a Mongo Draft UsageKey. This
        method is a wrapper around _location attribute that fixes the problem
        by calling map_into_course, which restores the run attribute.
        """
        return self._location.map_into_course(self.id)

    @property
    def number(self):
        """
        Returns this course's number.
        """
        return self.location.course

    @property
    def display_name_with_default(self):
        """
        Return reasonable display name for the course.
        """
        return course_metadata_utils.display_name_with_default(self.display_name, self.location)

    def has_started(self):
        """
        Returns whether the current time is past the start time.
        """
        return date_time.now(UTC()) > self.start

    def has_ended(self):
        """
        Returns whether (a) there is an end time specified and
                        (b) the current time is past it.
        """
        return date_time.now(UTC()) > self.end if self.end else False

    def start_datetime_text(self, format_string="SHORT_DATE"):
        """
        Returns the desired text corresponding the course's start date and time in UTC.  Prefers .advertised_start,
        then falls back to .start.
        """
        return course_metadata_utils.start_datetime_text(
            self.start,
            self.advertised_start,
            format_string,
            ugettext,
            strftime_localized
        )

    @property
    def start_date_is_still_default(self):
        """
        Checks if the start date set for the course is still default, i.e. .start has not been modified,
        and .advertised_start has not been set.
        """
        return course_metadata_utils.start_date_is_still_default(
            self.start,
            self.advertised_start,
        )

    def end_datetime_text(self, format_string="SHORT_DATE"):
        """
        Returns the end date or date_time for the course formatted as a string.
        """
        return course_metadata_utils.end_datetime_text(
            self.end,
            format_string,
            strftime_localized
        )

    def may_certify(self):
        """
        Return whether it is acceptable to show the student a certificate download link.
        """
        return course_metadata_utils.may_certify(
            self.certificates_display_behavior,
            self.certificates_show_before_end,
            self.has_ended()
        )

    @property
    def pre_requisite_courses(self):
        """
        Returns a list of ID strings for this course's prerequisite courses.
        """
        if not hasattr(self, '_pre_requisite_courses'):
            self._pre_requisite_courses = json.loads(self._pre_requisite_courses_json)
        return self._pre_requisite_courses
