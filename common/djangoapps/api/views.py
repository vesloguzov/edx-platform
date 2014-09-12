from django.contrib.auth.models import User, AnonymousUser
from django.conf import settings
from django.http import Http404

from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import detail_route
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from xmodule.error_module import ErrorDescriptor
from xmodule.modulestore.django import modulestore

from courseware.courses import get_course_by_id, get_courses
from student.models import CourseEnrollment

from api.serializers import UserSerializer, UID_PATTERN, CourseSerializer, CourseEnrollmentSerializer

class ApiKeyHeaderPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Check for permissions by matching the configured API key and header

        If settings.DEBUG is True and settings.EDX_API_KEY is not set or None,
        then allow the request. Otherwise, allow the request if and only if
        settings.EDX_API_KEY is set and the X-Edx-Api-Key HTTP header is
        present in the request and matches the setting.
        """
        # copied with some modifications from user_api
        api_key = getattr(settings, "EDX_API_KEY", '')
        return (
            (settings.DEBUG and not api_key) or
            (api_key and request.META.get("HTTP_X_EDX_API_KEY") == api_key)
        )

class UserViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    API for operating users.
    Username is used as a lookup url parameter (limited to alphanumeric and [.-_])
    """
    permission_classes = (ApiKeyHeaderPermission,)

    queryset = User.objects.select_related('profile__name')
    serializer_class = UserSerializer

    lookup_field = 'username'
    lookup_value_regex = UID_PATTERN

    @detail_route()
    def courses(self, request, *args, **kwargs):
        """
        Returns a list of all the courses user is enrolled in.
        """
        user = self.get_object()
        courses = self._get_enrollments(user)
        serializer = CourseEnrollmentSerializer(courses, many=True)
        return Response(serializer.data)

    @staticmethod
    def _get_enrollments(user):
        return [enrollment for enrollment in CourseEnrollment.enrollments_for_user(user)
                if not isinstance(modulestore().get_course(enrollment.course_id), ErrorDescriptor)]


class CourseViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    API for retrieving available courses.
    Course locator is used as lookup url parameter
    """
    permission_classes = (ApiKeyHeaderPermission,)

    serializer_class = CourseSerializer

    lookup_field = 'course_id'
    lookup_regex = settings.COURSE_ID_PATTERN

    def list(self, request, *args, **kwargs):
        self.object_list = self._get_available_courses()
        serializer = self.get_serializer(self.object_list, many=True)
        return Response(serializer.data)

    def _get_available_courses(self):
        # now only courses seen for everybody are shown
        return get_courses(AnonymousUser())

    def get_object(self, *args, **kwargs):
        course_id = self.kwargs.get(self.lookup_field, None)
        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        return get_course_by_id(course_key)
