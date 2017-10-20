# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_modes', '0001_verbose_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursemode',
            name='expiration_datetime_is_explicit',
            field=models.BooleanField(default=True),
        ),
    ]
