"""
Unittests for cleaning lms datastore after course deletion
"""
import json
import datetime
from unittest import skipUnless

from django.conf import settings
from django.core.management import call_command, CommandError

from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory

from student.tests.factories import UserFactory, CourseEnrollmentFactory
from student.roles import CourseInstructorRole, CourseStaffRole
from courseware.models import StudentModule


@skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
class CleanupDeletedCourseTest(SharedModuleStoreTestCase):
    """
    Tests for cleanup_deleted_course management command
    """

    def setUp(self):
        super(CleanupDeletedCourseTest, self).setUp()

        self.course = CourseFactory.create()
        chapter = ItemFactory.create(category='chapter', parent_location=self.course.location)
        section = ItemFactory.create(category='sequential', parent_location=chapter.location, due=datetime.datetime(2030, 9, 18, 11, 30, 00))
        vertical = ItemFactory.create(category='vertical', parent_location=section.location)
        component = ItemFactory.create(category='problem', parent_location=vertical.location)

        self.user = UserFactory()
        CourseEnrollmentFactory(user=self.user, course_id=self.course.id)

        from courseware.tests.factories import StudentModuleFactory
        for item in (chapter, section, vertical, component):
            StudentModuleFactory.create(
                student=self.user,
                course_id=self.course.id,
                module_state_key=item.scope_ids.usage_id,
                state=json.dumps({'state': unicode(item.scope_ids.usage_id)})
            )

    def test_cleanup_error_for_existing_course(self):
        with self.assertRaisesRegexp(CommandError, 'existing course'):
            call_command('cleanup_deleted_course', do_it=True, course_id=unicode(self.course.id))

    def test_cleanup(self):
        self._delete_course()
        self.assertNotEqual(StudentModule.objects.filter(course_id=self.course.id).count(), 0)

        call_command('cleanup_deleted_course', do_it=True, course_id=unicode(self.course.id))
        self.assertEqual(StudentModule.objects.filter(course_id=self.course.id).count(), 0)

    def _delete_course(self):
        """
        Delete course like cms management command
        """
        module_store = modulestore()
        with module_store.bulk_operations(self.course.id):
            module_store.delete_course(self.course.id, self.user.id)

        staff_role = CourseStaffRole(self.course.id)
        staff_role.remove_users(*staff_role.users_with_role())
        instructor_role = CourseInstructorRole(self.course.id)
        instructor_role.remove_users(*instructor_role.users_with_role())
