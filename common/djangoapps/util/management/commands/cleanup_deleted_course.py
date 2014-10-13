###
### Script for deleting a course
###
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from optparse import make_option
from opaque_keys.edx.keys import CourseKey
from opaque_keys import InvalidKeyError
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from xmodule.modulestore.django import modulestore

class Command(BaseCommand):
    help = '''Cleanup database after deletion of the course'''

class Command(BaseCommand):
    help = '''Delete a MongoDB backed course'''

    option_list = BaseCommand.option_list + (
        make_option('--do-it',
                    metavar='DO_IT',
                    dest='do_it',
                    action='store_true',
                    help='actually perform the cleanup'),

        make_option('-c', '--course-id',
                    metavar='COURSE_ID',
                    dest='course_id',
                    default=False,
                    help="course id"),
    )

    def handle(self, *args, **options):
        course_id = options['course_id']
        if not course_id:
            raise CommandError("You must specify a course-id")

        # try to parse the serialized course key into a CourseKey
        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            print("Course id {} could not be parsed as a CourseKey; falling back to SSCK.from_dep_str".format(course_id))
            course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)

        course = modulestore().get_course(course_key)
        if course:
            raise CommandError('Trying to perform a cleanup for existing course, forbidden!')

        connected_models = [m for m in models.get_models() if 'course_id' in m._meta.get_all_field_names()]
        connected_objects_count = 0

        for model in connected_models:
            connected_objects = model.objects.filter(course_id=course_key)
            _connected_objects_count = connected_objects.count()
            if _connected_objects_count:
                print '{}: {} objects to be deleted'.format(
                    model._meta.verbose_name, connected_objects.count()
                )
                connected_objects_count += _connected_objects_count
                if options['do_it']:
                    connected_objects.delete()
                    print 'DELETED'
        if not connected_objects_count:
            print 'No connected objects found'
        if not options['do_it']:
            print 'This was a dry run, call command with option --do-it to remove objects actually'
