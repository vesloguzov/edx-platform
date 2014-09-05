"""Django management command to create stub certificate (with 'generating' status) for the course"""

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

        result = _generate_cert_stubs(course, forced_grade=options['grade_value'])
        for status, certs in result.items():
            print '-' * 80
            print status.upper()
            for cert in certs:
                print cert.user.username, cert.user.id

def _generate_cert_stubs(course, forced_grade=None):
    enrolled_students = User.objects.filter(
        courseenrollment__course_id=course.id
    )

    factory = RequestFactory()
    request = factory.get('/')
    whitelist = CertificateWhitelist.objects.all()
    restricted = UserProfile.objects.filter(allow_certificate=False)

    results = {}
    for student in enrolled_students:
        cert = _generate_cert_stub_for_student(student, course, whitelist, restricted, request, forced_grade)
        if cert:
            results.setdefault(cert.status, []).append(cert)
    return results

def _generate_cert_stub_for_student(student, course, whitelist, restricted, request, forced_grade):
    VALID_STATUSES = [CertificateStatuses.generating,
                      CertificateStatuses.unavailable,
                      CertificateStatuses.deleted,
                      CertificateStatuses.error,
                      CertificateStatuses.notpassing]

    cert_status = certificate_status_for_student(student, course.id)['status']

    if cert_status not in VALID_STATUSES:
        return None

    # grade the student

    # re-use the course passed in optionally so we don't have to re-fetch everything
    # for every student
    profile = UserProfile.objects.get(user=student)
    profile_name = profile.name

    # Needed
    request.user = student
    request.session = {}

    course_name = course.display_name or course.id.to_deprecated_string()
    is_whitelisted = whitelist.filter(user=student, course_id=course.id, whitelist=True).exists()
    grade = grades.grade(student, request, course)
    enrollment_mode, __ = CourseEnrollment.enrollment_mode_for_user(student, course.id)
    mode_is_verified = (enrollment_mode == GeneratedCertificate.MODES.verified)
    user_is_verified = SoftwareSecurePhotoVerification.user_is_verified(student)
    user_is_reverified = SoftwareSecurePhotoVerification.user_is_reverified_for_all(course.id, student)
    cert_mode = enrollment_mode
    if (mode_is_verified and not (user_is_verified and user_is_reverified)):
        template_pdf = "certificate-template-{id.org}-{id.course}.pdf".format(id=course.id)
        cert_mode = GeneratedCertificate.MODES.honor
    if forced_grade:
        grade['grade'] = forced_grade

    cert, __ = GeneratedCertificate.objects.get_or_create(user=student, course_id=course.id)

    cert.mode = cert_mode
    cert.user = student
    cert.grade = grade['percent']
    cert.course_id = course.id
    cert.name = profile_name
    # Strip HTML from grade range label
    grade_contents = grade.get('grade', None)
    try:
        grade_contents = lxml.html.fromstring(grade_contents).text_content()
    except (TypeError, XMLSyntaxError, ParserError) as e:
        #   Despite blowing up the xml parser, bad values here are fine
        grade_contents = None

    if is_whitelisted or grade_contents is not None:

        # check to see whether the student is on the
        # the embargoed country restricted list
        # otherwise, put a new certificate request
        # on the queue

        if restricted.filter(user=student).exists():
            cert.status = CertificateStatuses.restricted
            cert.save()
        else:
            cert.status = CertificateStatuses.generating
            cert.save()
    else:
        cert.status = CertificateStatuses.notpassing
        cert.save()

    return cert
