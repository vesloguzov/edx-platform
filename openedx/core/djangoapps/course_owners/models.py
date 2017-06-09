"""
Models for information about course owners (usually persons who created the course)
for user courses page etc.

Migration Notes

If you make changes to this model, be sure to create an appropriate migration
file and check it in at the same time as your model changes. To do that,

1. Go to the edx-platform dir
2. ./manage.py lms schemamigration student --auto description_of_your_change
3. Add the migration file created in edx-platform/common/djangoapps/student/migrations/
"""
import logging

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy

from openedx.core.djangoapps.xmodule_django.models import CourseKeyField


log = logging.getLogger(__name__)


class CourseOwnership(models.Model):
    """
    Maps users to courses they own, e.g. courses that are shown in the list
    for particular users
    """

    user = models.ForeignKey(User, related_name='owned_courses')
    course_id = CourseKeyField(max_length=255, db_index=True)
    created = models.DateTimeField(auto_now_add=True, null=True, db_index=True)

    class Meta:  # pylint: disable=missing-docstring
        unique_together = (('user', 'course_id'),)
        ordering = ('user', 'course_id')
        verbose_name = ugettext_lazy('course ownership')
        verbose_name_plural = ugettext_lazy('course ownerships')

    def __unicode__(self):
        return (
            "[CourseOwnership] {}: {} ({})"
        ).format(self.user, self.course_id, self.created)


def create_new_course_ownership(course_id, user, **kwargs):  # pylint: disable=unused-argument
    """
    Assign owner for new course just created
    """
    assert user
    return CourseOwnership.objects.create(user=user, course_id=course_id)


def create_rerun_ownership(src_course_id, dst_course_id, **kwargs):  # pylint: disable=unused-argument
    """
    Copy owner(s) from the source course if possible or leave course unowned
    Return list of CourseOwnership objects
    """
    return [
        CourseOwnership.objects.create(
            user=ownership.user,
            course_id=dst_course_id
        ) for ownership in CourseOwnership.objects.filter(course_id=src_course_id)
    ]


def cleanup_deleted_course_ownership(course_id, **kwargs):  # pylint: disable=unused-argument
    """
    Remove any course ownership objects left after course deletion
    """

    log.info('Removing course ownership objects for deleted course {}'.format(course_id))
    CourseOwnership.objects.filter(course_id=course_id).delete()
