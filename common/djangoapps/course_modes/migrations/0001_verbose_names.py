# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import xmodule_django.models


class Migration(migrations.Migration):

    dependencies = [
        ('course_modes', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='coursemode',
            options={'verbose_name': 'course mode', 'verbose_name_plural': 'course modes'},
        ),
        migrations.AlterField(
            model_name='coursemode',
            name='currency',
            field=models.CharField(default=b'usd', max_length=8, verbose_name='Currency'),
        ),
        migrations.AlterField(
            model_name='coursemode',
            name='description',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
        migrations.AlterField(
            model_name='coursemodesarchive',
            name='course_id',
            field=xmodule_django.models.CourseKeyField(max_length=255, verbose_name='Course', db_index=True),
        ),
        migrations.AlterField(
            model_name='coursemodesarchive',
            name='currency',
            field=models.CharField(default=b'usd', max_length=8, verbose_name='Currency'),
        ),
        migrations.AlterField(
            model_name='coursemodesarchive',
            name='expiration_datetime',
            field=models.DateTimeField(default=None, null=True, verbose_name='Upgrade Deadline', blank=True),
        ),
        migrations.AlterField(
            model_name='coursemodesarchive',
            name='min_price',
            field=models.IntegerField(default=0, verbose_name='Price'),
        ),
        migrations.AlterField(
            model_name='coursemodesarchive',
            name='mode_display_name',
            field=models.CharField(max_length=255, verbose_name='Display name'),
        ),
        migrations.AlterField(
            model_name='coursemodesarchive',
            name='mode_slug',
            field=models.CharField(max_length=100, verbose_name='Mode'),
        ),
    ]
