import re

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from student.models import UserProfile, CourseEnrollment
from openedx.core.lib.courses import course_image_url
from certificates.models import certificate_status_for_student, CertificateStatuses
from certificates.api import get_certificate_url


UID_PATTERN = r'[\w.-]+'
UID_REGEX = re.compile('^%s$' % UID_PATTERN)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializes user and corresponding profile to unite object

    Represents username as uid (since it's a technical field),
    profile.name as name
    """
    uid = serializers.CharField(source='username', required=True, allow_blank=False, validators=[UniqueValidator(queryset=User.objects)])
    email = serializers.EmailField(required=False, allow_null=False, validators=[UniqueValidator(queryset=User.objects)])

    name = serializers.CharField(source='profile.name', default='', max_length=255, required=False, allow_blank=True)
    nickname = serializers.CharField(source='profile.nickname', default='', max_length=255, required=False, allow_blank=True)
    first_name = serializers.CharField(source='profile.first_name', default='', max_length=255, required=False, allow_blank=True)
    last_name = serializers.CharField(source='profile.last_name', default='', max_length=255, required=False, allow_blank=True)
    birthdate = serializers.DateField(source='profile.birthdate', default=None, required=False, allow_null=True)
    city = serializers.CharField(source='profile.city', default='', required=False, allow_blank=True)
    gender = serializers.ChoiceField(source='profile.gender', choices=UserProfile.GENDER_CHOICES,
                                     default=None, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('uid', 'email', 'name', 'nickname', 'first_name', 'last_name',
                  'birthdate', 'city', 'gender')
        lookup_field = 'uid'

    def validate_uid(self, value):
        """
        Validate additional uid constraints since uniqueness and presence are validated automatically
        """
        if value and not UID_REGEX.match(value):
            raise serializers.ValidationError(_('UID must consist of letters, digits, ".", "_" and "-"'))
        return value

    def validate(self, data):
        """
        Validate email presense on object creation
        """
        if not self.instance and not data.get('email', False):
            raise serializers.ValidationError({'email': self.error_messages['required']})
        return data

    def create(self, validated_data):
        data = validated_data.copy()
        profile_data = data.pop('profile')
        user = User.objects.create(**data)
        # bind updated profile to user for correct patch response
        user.profile = UserProfile.objects.create(user=user, **profile_data)
        CourseEnrollment.enroll_pending(user)
        return user

    def update(self, instance, validated_data):
        data = validated_data.copy()
        profile_data = data.pop('profile')

        user = super(UserSerializer, self).update(instance, data)
        profile = UserProfile.objects.get(user=user)
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()
        # bind updated profile to user for correct patch response
        user.profile = profile
        return user


class CourseSerializer(serializers.Serializer):
    course_id = serializers.CharField(source='id')
    name = serializers.CharField(source='display_name')
    description = serializers.SerializerMethodField()

    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    enrollment_start = serializers.DateTimeField()
    enrollment_end = serializers.DateTimeField()

    lowest_passing_grade = serializers.CharField()

    # categories???
    # student_count = serializers.IntegerField()
    # staff ???
    # registration_possible, ...

    image = serializers.SerializerMethodField()
    about_url = serializers.SerializerMethodField()
    root_url = serializers.SerializerMethodField()
    last_modification = serializers.DateTimeField(source='edited_on')

    def get_description(self, course):
        key = course.id.make_usage_key('about', 'short_description')
        try:
            description = modulestore().get_item(key).data
        except ItemNotFoundError:
            description = ''
        return description

    def get_image(self, course):
        url = course_image_url(course)
        return self._get_absolute_url(url)

    def get_about_url(self, course):
        url = reverse('about_course',
                      kwargs={'course_id': course.id.to_deprecated_string()})
        return self._get_absolute_url(url)

    def get_root_url(self, course):
        url = reverse('course_root',
                      kwargs={'course_id': course.id.to_deprecated_string()})
        return self._get_absolute_url(url)

    def _get_absolute_url(self, url):
        return self.context['request'].build_absolute_uri(url)


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializes enrollment information for course summary
    """
    uid = serializers.CharField(source='username', required=True, allow_blank=False, validators=[UniqueValidator(queryset=User.objects)])

    class Meta:
        model = CourseEnrollment
        fields = ('uid', 'mode', 'is_active', 'created')


class UserEnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializes enrollment information for user dashboard
    """
    grade = serializers.SerializerMethodField()
    certificate_url = serializers.SerializerMethodField()

    class Meta:
        model = CourseEnrollment
        fields = ('course_id', 'mode', 'grade', 'certificate_url')

    def get_grade(self, enrollment):
        certificate_status = self._get_certificate_status(enrollment)
        return certificate_status.get('grade')

    def get_certificate_url(self, enrollment):
        certificate_status = self._get_certificate_status(enrollment)
        if certificate_status['status'] != CertificateStatuses.downloadable:
            return None
        if certificate_status.get('download_url'):
            return certificate_status['download_url']
        else:
            url = get_certificate_url(course_id=enrollment.course_id, uuid=certificate_status['uuid'])
            return self.context['request'].build_absolute_uri(url)

    def _get_certificate_status(self, enrollment):
        if not hasattr(enrollment, '_certificate_status'):
            enrollment._certificate_status = certificate_status_for_student(
                enrollment.user, enrollment.course_id)
        return enrollment._certificate_status
