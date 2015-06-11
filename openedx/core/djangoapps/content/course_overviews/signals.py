"""
Signal handler for invalidating cached course overviews
"""

from django.dispatch.dispatcher import receiver

from xmodule.modulestore.django import SignalHandler
from .models import CourseOverview

@receiver(SignalHandler.course_published)
def listen_for_course_publish(_sender, course_key, **_kwargs):  # pylint: disable=unused-argument
    """
    Catches the signal that a course has been published in Studio and invalidates
    the corresponding CourseOverview cache entry if one exists.
    """
    CourseOverview.objects.filter(id=course_key).delete()
