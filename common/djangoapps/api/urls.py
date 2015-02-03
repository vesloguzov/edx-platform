from django.conf.urls import include, patterns, url
from routers import Router, NestedRouter

from api import views as api_views


api_router = Router()
api_router.register(r'users', api_views.UserViewSet, 'profile')
api_router.register(r'courses', api_views.CourseViewSet, base_name='course')

user_nested_router = NestedRouter(api_router, r'users', lookup='user')
user_nested_router.register(r'courses', api_views.EnrollmentViewSet, base_name='enrollment')

urlpatterns = api_router.urls
urlpatterns += user_nested_router.urls
