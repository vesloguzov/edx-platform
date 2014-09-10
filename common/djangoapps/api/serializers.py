from django.contrib.auth.models import User

from rest_framework import serializers
from student.models import UserProfile

class UserSerializer(serializers.ModelSerializer):
    uid = serializers.CharField(source='username')
    name = serializers.CharField(source='profile.name', max_length=255)

    class Meta:
        model = User
        fields = ('uid', 'email', 'name')
        lookup_field = 'uid'

    def restore_object(self, attrs, instance=None):
        profile_data = {'name': attrs.pop('profile.name')}
        instance = super(UserSerializer, self).restore_object(attrs, instance)
        instance._profile_data = profile_data
        return instance

    def save_object(self, user):
        profile_data = self.object._profile_data
        del(self.object._profile_data)

        super(UserSerializer, self).save_object(user)

        profile, _ = UserProfile.objects.get_or_create(user=self.object)
        profile.name = profile_data['name']
        profile.save()
