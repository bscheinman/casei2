# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-18 17:49
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ncaacards', '0002_userentry_apid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userentry',
            name='apid',
            field=models.UUIDField(default=uuid.uuid4, null=True, unique=True),
        ),
    ]
