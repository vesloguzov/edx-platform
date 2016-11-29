# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0005_verbose_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedcertificate',
            name='template_version',
            field=models.SlugField(default=b'', blank=True, help_text='Version of HTML certificate template used to render certificate. Should contain only latin letters, numbers, underscores or hyphens.', verbose_name='template version'),
        ),
    ]
