"""Django management command to create stub certificate (with 'generating' status) for the course"""

import os
import shutil
import urllib
import urlparse
import lxml.html
from lxml.etree import XMLSyntaxError, ParserError

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from xmodule.modulestore.django import modulestore

from django.core.urlresolvers import reverse
from django.conf import settings

from certificates.models import GeneratedCertificate
from certificates.models import CertificateStatuses


class Command(BaseCommand):
    help = """Create stub certificates (with 'generating' status) for the course"""

    option_list = BaseCommand.option_list + (
        make_option('-c', '--course',
                    metavar='COURSE_ID',
                    dest='course',
                    default=False,
                    help='The course id (e.g., mit/6-002x/circuits-and-electronics) for which the student named in'
                         '<username> should be graded'),
        make_option('-D', '--dir',
                    metavar='DIRECTORY',
                    dest='src_dir',
                    default=None,
                    help='The source directory with generated certificates to ba attached to the database entries'),
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


        if not options['src_dir']:
            raise CommandError("You must specify a directory")
        elif not os.path.exists(options['src_dir']) or not os.path.isdir(options['src_dir']):
            raise CommandError('You must specify an existing directory')

        print "Fetching course data for {0}".format(course_id)
        course = modulestore().get_course(course_id, depth=2)

        result = _attach_certificates(course, options['src_dir'])
        for status, values in result.items():
            print '-' * 80
            print status.upper()
            for v in values:
                print v

def _attach_certificates(course, src_dir):
    pending_certificates = GeneratedCertificate.objects.filter(course_id=course.id, status=CertificateStatuses.generating)
    files = {os.path.splitext(fn)[0]: fn for fn in os.listdir(src_dir) if fn.lower().endswith('.pdf')}

    result = {'attached': [], 'missing': []}
    for certificate in pending_certificates:
        filename = files.pop(certificate.user.username, None)
        if filename:
            _attach_certificate(os.path.join(src_dir, filename), certificate)
            result['attached'].append(certificate.user.username)
        else:
            result['missing'].append(certificate.user.username)
    result['files_left'] = files.values()
    return result

def _attach_certificate(src_filename, certificate):
    dst_dir = os.path.join(settings.CERT_STORAGE_PATH, certificate.download_uuid)
    dst_filename = 'Certificate_{}_{}.pdf'.format(certificate.course_id.org, certificate.course_id.course)
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    shutil.copy(src_filename, os.path.join(dst_dir, dst_filename))

    certificate.status = CertificateStatuses.downloadable
    certificate.download_url = os.path.join(
        settings.LMS_BASE, settings.CERT_URL, certificate.download_uuid, dst_filename
    )
    certificate.save()
