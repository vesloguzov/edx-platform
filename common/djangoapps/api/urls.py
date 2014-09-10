from django.conf.urls import include, patterns, url
from rest_framework import routers

from api import views as api_views


api_router = routers.DefaultRouter()
api_router.register(r'users', api_views.UserViewSet)

urlpatterns = api_router.urls
