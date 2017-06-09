# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import openedx.core.djangoapps.xmodule_django.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseOwnership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('course_id', openedx.core.djangoapps.xmodule_django.models.CourseKeyField(max_length=255, db_index=True)),
                ('created', models.DateTimeField(db_index=True, auto_now_add=True, null=True)),
                ('user', models.ForeignKey(related_name='owned_courses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('user', 'course_id'),
                'verbose_name': 'course ownership',
                'verbose_name_plural': 'course ownerships',
            },
        ),
        migrations.AlterUniqueTogether(
            name='courseownership',
            unique_together=set([('user', 'course_id')]),
        ),
    ]
