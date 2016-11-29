# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import certificates.models
from django.conf import settings
import xmodule_django.models
import django_extensions.db.fields.json


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0005_auto_20151208_0801'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='badgeassertion',
            options={'verbose_name': 'badge assertion', 'verbose_name_plural': 'badge assertions'},
        ),
        migrations.AlterModelOptions(
            name='badgeimageconfiguration',
            options={'verbose_name': 'badge image configuration', 'verbose_name_plural': 'badge image configurations'},
        ),
        migrations.AlterModelOptions(
            name='certificategenerationconfiguration',
            options={'ordering': ('-change_date',), 'verbose_name': 'certificate generation configuration', 'verbose_name_plural': 'certificate generation configurations'},
        ),
        migrations.AlterModelOptions(
            name='certificategenerationcoursesetting',
            options={'get_latest_by': 'created', 'verbose_name': 'certificate generation course setting', 'verbose_name_plural': 'certificate generation course settings'},
        ),
        migrations.AlterModelOptions(
            name='certificategenerationhistory',
            options={'verbose_name': 'certificate generation history item', 'verbose_name_plural': 'certificate generation history'},
        ),
        migrations.AlterModelOptions(
            name='certificatehtmlviewconfiguration',
            options={'ordering': ('-change_date',), 'verbose_name': 'HTML certificates configuration', 'verbose_name_plural': 'HTML certificates configurations'},
        ),
        migrations.AlterModelOptions(
            name='certificatetemplate',
            options={'get_latest_by': 'created', 'verbose_name': 'certificate template', 'verbose_name_plural': 'certificate templates'},
        ),
        migrations.AlterModelOptions(
            name='certificatetemplateasset',
            options={'get_latest_by': 'created', 'verbose_name': 'certificate template asset', 'verbose_name_plural': 'certificate template assets'},
        ),
        migrations.AlterModelOptions(
            name='certificatewhitelist',
            options={'verbose_name': 'certificate exception', 'verbose_name_plural': 'certificate exceptions'},
        ),
        migrations.AlterModelOptions(
            name='examplecertificateset',
            options={'get_latest_by': 'created', 'verbose_name': 'example certificate set', 'verbose_name_plural': 'example certificate sets'},
        ),
        migrations.AlterField(
            model_name='badgeassertion',
            name='course_id',
            field=xmodule_django.models.CourseKeyField(default=None, max_length=255, verbose_name='course', blank=True),
        ),
        migrations.AlterField(
            model_name='badgeassertion',
            name='data',
            field=django_extensions.db.fields.json.JSONField(verbose_name='data'),
        ),
        migrations.AlterField(
            model_name='badgeassertion',
            name='mode',
            field=models.CharField(max_length=100, verbose_name='mode'),
        ),
        migrations.AlterField(
            model_name='badgeassertion',
            name='user',
            field=models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='badgeimageconfiguration',
            name='default',
            field=models.BooleanField(default=False, help_text='Set this value to True if you want this image to be the default image for any course modes that do not have a specified badge image. You can have only one default image.', verbose_name='default'),
        ),
        migrations.AlterField(
            model_name='badgeimageconfiguration',
            name='icon',
            field=models.ImageField(help_text='Badge images must be square PNG files. The file size should be under 250KB.', upload_to=b'badges', verbose_name='icon', validators=[certificates.models.validate_badge_image]),
        ),
        migrations.AlterField(
            model_name='badgeimageconfiguration',
            name='mode',
            field=models.CharField(help_text='The course mode for this badge image. For example, "verified" or "honor".', unique=True, max_length=125, verbose_name='mode'),
        ),
        migrations.AlterField(
            model_name='certificategenerationcoursesetting',
            name='course_key',
            field=xmodule_django.models.CourseKeyField(max_length=255, verbose_name='course', db_index=True),
        ),
        migrations.AlterField(
            model_name='certificategenerationcoursesetting',
            name='enabled',
            field=models.BooleanField(default=False, verbose_name='enabled'),
        ),
        migrations.AlterField(
            model_name='certificategenerationhistory',
            name='course_id',
            field=xmodule_django.models.CourseKeyField(max_length=255, verbose_name='course'),
        ),
        migrations.AlterField(
            model_name='certificategenerationhistory',
            name='generated_by',
            field=models.ForeignKey(verbose_name='generated by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='certificategenerationhistory',
            name='instructor_task',
            field=models.ForeignKey(verbose_name='instructor task', to='instructor_task.InstructorTask'),
        ),
        migrations.AlterField(
            model_name='certificategenerationhistory',
            name='is_regeneration',
            field=models.BooleanField(default=False, verbose_name='regeneration'),
        ),
        migrations.AlterField(
            model_name='certificatehtmlviewconfiguration',
            name='configuration',
            field=models.TextField(help_text='Certificate HTML View Parameters (JSON)', verbose_name='configuration'),
        ),
        migrations.AlterField(
            model_name='certificatetemplate',
            name='course_key',
            field=xmodule_django.models.CourseKeyField(db_index=True, max_length=255, null=True, verbose_name='course', blank=True),
        ),
        migrations.AlterField(
            model_name='certificatetemplate',
            name='description',
            field=models.CharField(help_text='Description and/or admin notes.', max_length=255, null=True, verbose_name='description', blank=True),
        ),
        migrations.AlterField(
            model_name='certificatetemplate',
            name='is_active',
            field=models.BooleanField(default=False, help_text='On/Off switch.', verbose_name='active'),
        ),
        migrations.AlterField(
            model_name='certificatetemplate',
            name='mode',
            field=models.CharField(default=b'honor', choices=[(b'verified', b'verified'), (b'honor', b'honor'), (b'audit', b'audit'), (b'professional', b'professional'), (b'no-id-professional', b'no-id-professional')], max_length=125, blank=True, help_text='The course mode for this template.', null=True, verbose_name='mode'),
        ),
        migrations.AlterField(
            model_name='certificatetemplate',
            name='name',
            field=models.CharField(help_text='Name of template.', max_length=255, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='certificatetemplate',
            name='organization_id',
            field=models.IntegerField(help_text='Organization of template.', null=True, verbose_name='organization', db_index=True, blank=True),
        ),
        migrations.AlterField(
            model_name='certificatetemplate',
            name='template',
            field=models.TextField(help_text='Django template HTML.', verbose_name='template'),
        ),
        migrations.AlterField(
            model_name='certificatetemplateasset',
            name='asset',
            field=models.FileField(help_text='Asset file. It could be an image or css file.', upload_to=certificates.models.template_assets_path, max_length=255, verbose_name='asset'),
        ),
        migrations.AlterField(
            model_name='certificatetemplateasset',
            name='description',
            field=models.CharField(help_text='Description of the asset.', max_length=255, null=True, verbose_name='description', blank=True),
        ),
        migrations.AlterField(
            model_name='certificatewhitelist',
            name='course_id',
            field=xmodule_django.models.CourseKeyField(default=None, max_length=255, verbose_name='course', blank=True),
        ),
        migrations.AlterField(
            model_name='certificatewhitelist',
            name='notes',
            field=models.TextField(default=None, null=True, verbose_name='notes'),
        ),
        migrations.AlterField(
            model_name='certificatewhitelist',
            name='user',
            field=models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='certificatewhitelist',
            name='whitelist',
            field=models.BooleanField(default=0, verbose_name='whitelist'),
        ),
        migrations.AlterField(
            model_name='examplecertificate',
            name='description',
            field=models.CharField(help_text="A human-readable description of the example certificate.  For example, 'verified' or 'honor' to differentiate between two types of certificates.", max_length=255, verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='examplecertificate',
            name='example_cert_set',
            field=models.ForeignKey(verbose_name='example certificate set', to='certificates.ExampleCertificateSet'),
        ),
        migrations.AlterField(
            model_name='examplecertificateset',
            name='course_key',
            field=xmodule_django.models.CourseKeyField(max_length=255, verbose_name='course', db_index=True),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='course_id',
            field=xmodule_django.models.CourseKeyField(default=None, max_length=255, verbose_name='course', blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='distinction',
            field=models.BooleanField(default=False, verbose_name='distinction'),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='download_url',
            field=models.CharField(default=b'', max_length=128, verbose_name='download URL', blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='download_uuid',
            field=models.CharField(default=b'', max_length=32, verbose_name='download UUID', blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='error_reason',
            field=models.CharField(default=b'', max_length=512, verbose_name='error reason', blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='grade',
            field=models.CharField(default=b'', max_length=5, verbose_name='grade', blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='key',
            field=models.CharField(default=b'', max_length=32, verbose_name='key', blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='mode',
            field=models.CharField(default=b'honor', max_length=32, verbose_name='mode', choices=[(b'verified', b'verified'), (b'honor', b'honor'), (b'audit', b'audit'), (b'professional', b'professional'), (b'no-id-professional', b'no-id-professional')]),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='modified_date',
            field=models.DateTimeField(auto_now=True, verbose_name='modified'),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='name',
            field=models.CharField(max_length=255, verbose_name='name', blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='status',
            field=models.CharField(default=b'unavailable', max_length=32, verbose_name='status'),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='user',
            field=models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='generatedcertificate',
            name='verify_uuid',
            field=models.CharField(default=b'', max_length=32, verbose_name='verify UUID', db_index=True, blank=True),
        ),
    ]
