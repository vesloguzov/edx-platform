from django.conf.urls import include, patterns, url
from routers import Router

from api import views as api_views


api_router = Router()
api_router.register(r'users', api_views.UserViewSet)
api_router.register(r'courses', api_views.CourseViewSet, base_name='course')

urlpatterns = api_router.urls
