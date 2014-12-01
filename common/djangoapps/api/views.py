from django.contrib.auth.models import User, AnonymousUser
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from xmodule.error_module import ErrorDescriptor
from xmodule.modulestore.django import modulestore

from courseware.courses import get_course_by_id, get_courses
from student.models import CourseEnrollment
from student.views import (
    enroll_student_with_default_mode, send_enrollment_email,
    EnrollmentError, EnrollmentModeRequiredException
)

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
                  # mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  # mixins.ListModelMixin,
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

    @list_route()
    def last_modification(self, request, *args, **kwargs):
        courses = self._get_available_courses()
        return Response(max(course.edited_on for course in courses) if courses else None)

    def _get_available_courses(self):
        # now only courses seen for everybody are shown
        return get_courses(AnonymousUser())

    def get_object(self, *args, **kwargs):
        course_id = self.kwargs.get(self.lookup_field, None)
        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        return get_course_by_id(course_key)


class EnrollmentViewSet(viewsets.GenericViewSet):
    permission_classes = (ApiKeyHeaderPermission,)

    serializer_class = CourseEnrollmentSerializer

    lookup_field = 'course_id'
    lookup_regex = settings.COURSE_ID_PATTERN

    def list(self, request, *args, **kwargs):
        enrollments = self._get_enrollments(*args, **kwargs)
        serializer = CourseEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @detail_route(methods=['post'])
    def enroll(self, request, *args, **kwargs):
        user = self._get_user(*args, **kwargs)
        course = self._get_course(*args, **kwargs)
        try:
            enrollment = enroll_student_with_default_mode(user, course, auto_register=False)
            if settings.FEATURES.get('SEND_ENROLLMENT_EMAIL'):
                send_enrollment_email(user, course, use_https_for_links=request.is_secure())
        except EnrollmentModeRequiredException:
            return Response({'detail': _('Enrollment mode required')},
                            status=status.HTTP_400_BAD_REQUEST)
        except EnrollmentError as e:
            return Response({'detail': e.message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = CourseEnrollmentSerializer(enrollment)
            return Response(serializer.data)

    @detail_route(methods=['post'])
    def unenroll(self, request, *args, **kwargs):
        user = self._get_user(*args, **kwargs)
        course_id = self.kwargs.get(self.lookup_field, None)
        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)

        if not CourseEnrollment.is_enrolled(user, course_key):
            return Response({'detail': _("User is not enrolled in this course")},
                            status=status.HTTP_400_BAD_REQUEST)
        CourseEnrollment.unenroll(user, course_key)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_enrollments(self, *args, **kwargs):
        user = self._get_user(*args, **kwargs)
        return [enrollment for enrollment in CourseEnrollment.enrollments_for_user(user)
                if not isinstance(modulestore().get_course(enrollment.course_id), ErrorDescriptor)]

    def _get_user(self, *args, **kwargs):
        username = self.kwargs['user_username']
        return get_object_or_404(User, username=username)

    def _get_course(self, *args, **kwargs):
        course_id = self.kwargs.get(self.lookup_field, None)
        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        return get_course_by_id(course_key)
