from django.contrib.auth.models import User, AnonymousUser
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from rest_framework import viewsets, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import NotFound
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from xmodule.error_module import ErrorDescriptor
from xmodule.modulestore.django import modulestore

from courseware.courses import get_course, get_courses
from course_modes.models import CourseMode
from student.models import CourseEnrollment, CourseEnrollmentException, AlreadyEnrolledError, NonExistentCourseError
from student.views import send_enrollment_email

from lek_api.serializers import UserSerializer, UID_PATTERN, CourseSerializer, CourseEnrollmentSerializer
from lek_api.put_as_create import AllowPUTAsCreateMixin


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


class ServerAPIViewSet(viewsets.GenericViewSet):
    authentication_classes = ()
    permission_classes = (ApiKeyHeaderPermission,)

    def _get_course_from_key_string(self, course_id):
        try:
            course_key = CourseKey.from_string(course_id)
            course = get_course(course_key)
        except (InvalidKeyError, ValueError):
            raise NotFound(detail=_("No course '{}' found").format(course_id))
        else:
            return course


class UserViewSet(AllowPUTAsCreateMixin,
                  mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  # mixins.ListModelMixin,
                  ServerAPIViewSet):
    """
    API for operating users.
    Username is used as a lookup url parameter (limited to alphanumeric and [.-_])
    """
    queryset = User.objects.select_related('profile__name')
    serializer_class = UserSerializer

    lookup_field = 'username'
    lookup_value_regex = UID_PATTERN


class CourseViewSet(mixins.RetrieveModelMixin, ServerAPIViewSet):
    """
    API for retrieving available courses.
    Course locator is used as lookup url parameter
    """
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
        return self._get_course_from_key_string(course_id)


class EnrollmentViewSet(ServerAPIViewSet):
    serializer_class = CourseEnrollmentSerializer

    lookup_field = 'course_id'
    lookup_regex = settings.COURSE_ID_PATTERN

    ALLOWED_COURSE_MODES = (
        CourseMode.AUDIT,
        CourseMode.HONOR,
        CourseMode.VERIFIED,
        CourseMode.PROFESSIONAL,
        CourseMode.NO_ID_PROFESSIONAL_MODE,
        CourseMode.CREDIT_MODE,
    )

    def list(self, request, *args, **kwargs):
        enrollments = self._get_enrollments(*args, **kwargs)
        serializer = CourseEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @detail_route(methods=['post'])
    def enroll(self, request, *args, **kwargs):
        """
        Enroll student with forced mode

        Overrides enrollment mode for already enrolled student
        """
        user = self._get_user(*args, **kwargs)
        course_id = self._get_course_id(*args, **kwargs)
        skip_enrollment_email = request.data.get('skip_enrollment_email', False)
        mode = request.data.get('mode', CourseMode.DEFAULT_MODE_SLUG)

        if mode not in self.ALLOWED_COURSE_MODES:
            return Response({'detail': u'Invalid course mode: {}'.format(mode)},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            # create new enrollment
            enrollment = CourseEnrollment.enroll(user, course_id, mode, check_access=True)
        except AlreadyEnrolledError:
            # update existing enrollment with current mode
            enrollment = CourseEnrollment.objects.get(user=user, course_id=course_id)
            enrollment.update_enrollment(is_active=True, mode=mode)
        except NonExistentCourseError:
            raise NotFound(detail=u"No course '{}' found".format(course_id))
        except CourseEnrollmentException as e:
            return Response({'detail': e.message or u"Enrollment failed ({})".format(e.__class__.__name__)},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if settings.FEATURES.get('SEND_ENROLLMENT_EMAIL') and not skip_enrollment_email:
                course = get_course(course_id)
                send_enrollment_email(user, course, use_https_for_links=request.is_secure())
        serializer = CourseEnrollmentSerializer(enrollment)
        return Response(serializer.data)

    @detail_route(methods=['post'])
    def unenroll(self, request, *args, **kwargs):
        user = self._get_user(*args, **kwargs)
        course_id = self.kwargs.get(self.lookup_field, None)
        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            raise NotFound(detail=_("No course '{}' found").format(course_id))

        if not CourseEnrollment.is_enrolled(user, course_key):
            try:
                get_course(course_key)
            except ValueError:
                raise NotFound(detail=u"No course '{}' found".format(course_id))
            else:
                return Response({'detail': u"User is not enrolled in this course"},
                                status=status.HTTP_400_BAD_REQUEST)

        CourseEnrollment.unenroll(user, course_key)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_enrollments(self, *args, **kwargs):
        user = self._get_user(*args, **kwargs)
        return [enrollment for enrollment in CourseEnrollment.enrollments_for_user(user)
                if not isinstance(modulestore().get_course(enrollment.course_id), ErrorDescriptor)]

    def _get_user(self, *args, **kwargs):
        username = self.kwargs['user_username']
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise NotFound(detail=u"No user with uid '{}' found".format(username))

    def _get_course(self, *args, **kwargs):
        course_id = self.kwargs.get(self.lookup_field, None)
        return self._get_course_from_key_string(course_id)

    def _get_course_id(self, *args, **kwargs):
        course_id = self.kwargs.get(self.lookup_field, None)
        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            raise NotFound(detail=u"Invalid course id '{}'".format(course_id))
        else:
            return course_key
