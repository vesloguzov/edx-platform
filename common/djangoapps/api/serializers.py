import re

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from student.models import UserProfile

UID_REGEX = re.compile('^[\w.-]+$')

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
