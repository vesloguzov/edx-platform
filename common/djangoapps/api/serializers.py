import re

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError
from rest_framework import serializers
from student.models import UserProfile, CourseEnrollment
from courseware.courses import course_image_url

UID_PATTERN = r'[\w.-]+'
UID_REGEX = re.compile('^%s$' % UID_PATTERN)

class UserSerializer(serializers.ModelSerializer):
    """
    Serializes user and corresponding profile to unite object

    Represents username as uid (since it's a technical field),
    profile.name as name
    """
    uid = serializers.CharField(source='username', required=True)
    name = serializers.CharField(source='profile.name', max_length=255, required=False)

    class Meta:
        model = User
        fields = ('uid', 'email', 'name')
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
        profile_data = {'name': attrs.pop('profile.name', '')}
        instance = super(UserSerializer, self).restore_object(attrs, instance)
        instance._profile_data = profile_data
        return instance

    def save_object(self, obj, **kwargs):
        profile_data = self.object._profile_data
        del(self.object._profile_data)

        super(UserSerializer, self).save_object(obj)

        profile, _ = UserProfile.objects.get_or_create(user=self.object)
        profile.name = profile_data['name']
        profile.save()
        # bind updated profile to user for correct patch response
        self.object.profile = profile


class CourseSerializer(serializers.Serializer):
    course_id = serializers.CharField(source='id')
    name = serializers.CharField(source='display_name')
    description = serializers.SerializerMethodField('get_description')

    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    enrollment_start = serializers.DateTimeField()
    enrollment_end = serializers.DateTimeField()

    # categories???
    # student_count = serializers.IntegerField()
    # staff ???
    # registration_possible, ...

    image = serializers.SerializerMethodField('get_image_url')
    last_modification = serializers.DateTimeField(source='edited_on')

    def get_description(self, course):
        key = course.id.make_usage_key('about', 'short_description')
        try:
            description = modulestore().get_item(key).data
        except ItemNotFoundError:
            description = ''
        return description

    def get_image_url(self, course):
        return course_image_url(course)


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseEnrollment
        fields = ('course_id', 'mode', 'is_active')
