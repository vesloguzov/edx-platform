# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0003_data__default_modes'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='generatedcertificate',
            options={'verbose_name': 'certificate', 'verbose_name_plural': 'certificates'},
        ),
    ]
