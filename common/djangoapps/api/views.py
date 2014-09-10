from django.contrib.auth.models import User
from django.conf import settings

from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import permissions

from api.serializers import UserSerializer

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
    ViewSet for users implementing all operations except destroying
    Uses username as a lookup url parameter (limited to alphanumeric and [.-_])
    """
    permission_classes = (ApiKeyHeaderPermission,)

    queryset = User.objects.select_related('profile__name')
    serializer_class = UserSerializer

    lookup_field = 'username'
    lookup_regex = '^[\w.-]+$' # standard regex '^[\w.@+-]+$' does not suit for url
