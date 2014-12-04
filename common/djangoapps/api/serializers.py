import re

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError
from rest_framework import serializers

from student.models import UserProfile, CourseEnrollment
from courseware.courses import course_image_url
from certificates.models import GeneratedCertificate


UID_PATTERN = r'[\w.-]+'
UID_REGEX = re.compile('^%s$' % UID_PATTERN)

class UserSerializer(serializers.ModelSerializer):
    """
    Serializes user and corresponding profile to unite object

    Represents username as uid (since it's a technical field),
    profile.name as name
    """
    uid = serializers.CharField(source='username', required=True)
    name = serializers.CharField(source='profile.name', default='', max_length=255, required=False)
    nickname = serializers.CharField(source='profile.nickname', default='', max_length=255, required=False)
    first_name = serializers.CharField(source='profile.first_name', default='', max_length=255, required=False)
    last_name = serializers.CharField(source='profile.last_name', default='', max_length=255, required=False)
    birthdate = serializers.DateField(source='profile.birthdate', default='', required=False)

    class Meta:
        model = User
        fields = ('uid', 'email', 'name', 'nickname', 'first_name', 'last_name', 'birthdate')
        lookup_field = 'uid'

    def validate_uid(self, attrs, source):
        """
        Validate additional uid constraints since uniqueness and presence are validated automatically
        """
        value = attrs.get(source)
        if value and not UID_REGEX.match(value):
            raise serializers.ValidationError(_('UID must consist of letters, digits, ".", "_" and "-"'))
        return attrs

    def restore_object(self, attrs, instance=None):
        profile_data = self._pop_profile_data(attrs)
        instance = super(UserSerializer, self).restore_object(attrs, instance)
        instance._profile_data = profile_data
        return instance

    def save_object(self, obj, **kwargs):
        profile_data = self.object._profile_data
        del(self.object._profile_data)

        super(UserSerializer, self).save_object(obj)

        profile, _ = UserProfile.objects.get_or_create(user=self.object)
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()
        # bind updated profile to user for correct patch response
        self.object.profile = profile

    def _pop_profile_data(self, attrs):
        profile_data = {}
        for source in attrs.keys():
            if source.startswith('profile.'):
                profile_field_name = source.split('.')[-1]
                profile_data[profile_field_name] = attrs.pop(source, None)
        return profile_data


class CourseSerializer(serializers.Serializer):
    course_id = serializers.CharField(source='id')
    name = serializers.CharField(source='display_name')
    description = serializers.SerializerMethodField('get_description')

    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    enrollment_start = serializers.DateTimeField()
    enrollment_end = serializers.DateTimeField()

    lowest_passing_grade = serializers.CharField(source='lowest_passing_grade')

    # categories???
    # student_count = serializers.IntegerField()
    # staff ???
    # registration_possible, ...

    image = serializers.SerializerMethodField('get_image_url')
    about_url = serializers.SerializerMethodField('get_about_course_url')
    root_url = serializers.SerializerMethodField('get_root_course_url')
    last_modification = serializers.DateTimeField(source='edited_on')

    def get_description(self, course):
        key = course.id.make_usage_key('about', 'short_description')
        try:
            description = modulestore().get_item(key).data
        except ItemNotFoundError:
            description = ''
        return description

    def get_image_url(self, course):
        url = course_image_url(course)
        return self._get_absolute_url(url)

    def get_about_course_url(self, course):
        url = reverse('about_course',
                kwargs={'course_id': course.id.to_deprecated_string()})
        return self._get_absolute_url(url)

    def get_root_course_url(self, course):
        url = reverse('course_root',
                kwargs={'course_id': course.id.to_deprecated_string()})
        return self._get_absolute_url(url)

    def _get_absolute_url(self, url):
        return self.context['request'].build_absolute_uri(url)


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    grade = serializers.SerializerMethodField('get_grade')
    certificate_url = serializers.SerializerMethodField('get_certificate_url')

    class Meta:
        model = CourseEnrollment
        fields = ('course_id', 'mode', 'grade', 'certificate_url')

    def get_grade(self, enrollment):
        certificate = self._get_certificate(enrollment)
        return certificate.grade if certificate else None

    def get_certificate_url(self, enrollment):
        certificate = self._get_certificate(enrollment)
        return certificate.download_url if certificate else None

    def _get_certificate(self, enrollment):
        if not hasattr(enrollment, '_certificate'):
            enrollment._certificate = GeneratedCertificate.certificate_for_student(
                                 enrollment.user, enrollment.course_id)
        return enrollment._certificate
