from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework import mixins
from api.serializers import UserSerializer

class UserViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    ViewSet for users implementing all operations except destroying
    """
    queryset = User.objects.select_related('profile__name')
    serializer_class = UserSerializer

    lookup_field = 'username'
    lookup_regex = '^[\w.-]+$' # standard regex '^[\w.@+-]+$' does not suit for url

    # paginate_by = 10
    # paginate_by_param = "page_size"
