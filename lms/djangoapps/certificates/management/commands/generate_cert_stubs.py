"""Django management command to create stub certificate (with 'generating' status) for the course"""

import json
import uuid
import lxml.html
from lxml.etree import XMLSyntaxError, ParserError

from optparse import make_option
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from xmodule.modulestore.django import modulestore

from certificates.models import GeneratedCertificate
from certificates.models import certificate_status_for_student
from certificates.models import CertificateStatuses
from certificates.models import CertificateWhitelist

from courseware import grades
from django.test.client import RequestFactory
from student.models import UserProfile, CourseEnrollment
from verify_student.models import SoftwareSecurePhotoVerification

# JSON_KEYS
USERNAME_KEY = 'uid'
GRADE_KEY = 'grade'
DISTINCTION_KEY = 'distinction'
NAME_KEY = 'name'

class Command(BaseCommand):
    help = """Create stub certificates (with 'generating' status) for the course"""

    option_list = BaseCommand.option_list + (
        make_option('-c', '--course',
                    metavar='COURSE_ID',
                    dest='course',
                    default=False,
                    help='The course id (e.g., mit/6-002x/circuits-and-electronics) for which the student named in'
                         '<username> should be graded'),
        make_option('-G', '--grade',
                    metavar='GRADE',
                    dest='grade_value',
                    default=None,
                    help='The grade string, such as "Distinction", which should be passed to the certificate agent'),
        make_option('-f', '--file-input',
                    metavar='FILE_INPUT',
                    dest='input_file',
                    default=False,
                    help='The name of a JSON file with uids, names, grades and other information for certificates generation'),
        make_option('-U', '--create-uids',
                    metavar='CREATE_UUIDS',
                    dest='create_uuids',
                    default=False,
                    help='create uuids for certificates'),
    )

    def handle(self, *args, **options):
        if options['course']:
            # try to parse out the course from the serialized form
            try:
                course_id = CourseKey.from_string(options['course'])
            except InvalidKeyError:
                print("Course id {} could not be parsed as a CourseKey; falling back to SSCK.from_dep_str".format(options['course']))
                course_id = SlashSeparatedCourseKey.from_deprecated_string(options['course'])
        else:
            raise CommandError("You must specify a course")

        print "Fetching course data for {0}".format(course_id)
        course = modulestore().get_course(course_id, depth=2)

        if options['input_file']:
            print 'Generating stubs from json...'
            result = _generate_cert_stubs_from_json(course, options['input_file'], options['create_uuids'])
        else:
            print 'Generating stubs...'
            result = _generate_cert_stubs(course, forced_grade=options['grade_value'], create_uuids=options['create_uuids'])
        for status, certs in result.items():
            print '-' * 80
            print status.upper()
            for cert in certs:
                print cert.user.username, cert.grade

def _generate_cert_stubs(course, forced_grade=None, create_uuids=False):
    enrolled_students = User.objects.filter(
        courseenrollment__course_id=course.id
    )

    factory = RequestFactory(HTTP_HOST='127.0.0.1')
    request = factory.get('/')
    whitelist = CertificateWhitelist.objects.all()
    restricted = UserProfile.objects.filter(allow_certificate=False)

    results = {}
    for student in enrolled_students:
        if _can_generate_certificate_for_student(student, course):
            cert = _generate_cert_stub_for_student(student, course, whitelist, restricted, request, forced_grade, create_uuids)
            results.setdefault(cert.status, []).append(cert)
        else:
            results.setdefault('INVALID', []).append(GeneratedCertificate.objects.get(user=student, course_id=course.id))
    return results


def _generate_cert_stubs_from_json(course, source_file, create_uuids=False):
    with open(source_file) as f:
        data = json.load(f)

    enrolled_students = User.objects.filter(courseenrollment__course_id=course.id)
    if enrolled_students.filter(username__in=[item[USERNAME_KEY] for item in data]).count() < len(data):
        raise CommandError('Extra students found in file, exiting')

    results = {}
    for item in data:
        student = enrolled_students.get(username=item[USERNAME_KEY])
        if _can_generate_certificate_for_student(student, course):
            if create_uuids:
                item['download_uuid'] = uuid.uuid4().hex
            cert = _generate_cert_stub_for_student_from_json(student, course, item)
            results.setdefault(cert.status, []).append(cert)
        else:
            results.setdefault('INVALID', []).append(GeneratedCertificate.objects.get(user=student, course_id=course.id))
    return results


def _generate_cert_stub_for_student(student, course, whitelist, restricted, request, forced_grade, create_uuids):
    if not _can_generate_certificate_for_student(student, course):
        return None

    # grade the student
    # Needed
    request.user = student
    request.session = {}
    grade = grades.grade(student, request, course)
    if forced_grade:
        grade['grade'] = forced_grade
    grade_contents = grade.get('grade', None)
    try:
        grade_contents = lxml.html.fromstring(grade_contents).text_content()
    except (TypeError, XMLSyntaxError, ParserError) as e:
        #   Despite blowing up the xml parser, bad values here are fine
        grade_contents = None

    # course_name = course.display_name or course.id.to_deprecated_string()
    is_whitelisted = whitelist.filter(user=student, course_id=course.id, whitelist=True).exists()

    cert_data = {
        'mode': _get_certificate_mode(student, course),
        'grade': grade['percent'],
        'name': student.profile.name,
    }
    if create_uuids:
        cert_data['download_uuid'] = uuid.uuid4().hex

    if is_whitelisted or grade_contents is not None:

        # check to see whether the student is on the
        # the embargoed country restricted list
        # otherwise, put a new certificate request
        # on the queue

        if restricted.filter(user=student).exists():
            cert_data['status'] = CertificateStatuses.restricted
        else:
            cert_data['status'] = CertificateStatuses.generating
    else:
        cert_data['status'] = CertificateStatuses.notpassing
    cert = _update_or_create_certificate_stub(student, course, cert_data)

    return cert


def _generate_cert_stub_for_student_from_json(student, course, data):
    cert_data = {
        'mode': _get_certificate_mode(student, course),
        'grade': data[GRADE_KEY],
        'name': data[NAME_KEY],
        'status': CertificateStatuses.generating,
        'download_uuid': data['download_uuid'],
    }
    return _update_or_create_certificate_stub(student, course, cert_data)


def _get_certificate_mode(student, course):
    enrollment_mode, __ = CourseEnrollment.enrollment_mode_for_user(student, course.id)
    mode_is_verified = (enrollment_mode == GeneratedCertificate.MODES.verified)
    user_is_verified = SoftwareSecurePhotoVerification.user_is_verified(student)
    user_is_reverified = SoftwareSecurePhotoVerification.user_is_reverified_for_all(course.id, student)
    cert_mode = enrollment_mode
    if (mode_is_verified and not (user_is_verified and user_is_reverified)):
        return GeneratedCertificate.MODES.honor
    else:
        return enrollment_mode

def _can_generate_certificate_for_student(student, course):
    VALID_STATUSES = [CertificateStatuses.generating,
                      CertificateStatuses.unavailable,
                      CertificateStatuses.deleted,
                      CertificateStatuses.error,
                      CertificateStatuses.notpassing]
    cert_status = certificate_status_for_student(student, course.id)['status']
    return cert_status in VALID_STATUSES


def _update_or_create_certificate_stub(student, course, data):
    cert, __ = GeneratedCertificate.objects.get_or_create(user=student, course_id=course.id)
    cert.mode = data['mode']
    cert.grade = data['grade']
    cert.name = data['name']
    cert.status = data['status']
    if 'download_uuid' in data:
        cert.download_uuid = data['download_uuid']
    cert.save()
    return cert
