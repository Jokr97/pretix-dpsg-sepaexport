# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-21 11:45
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('pretixbase', '0051_auto_20170206_2027_squashed_0057_auto_20170501_2116'),
    ]

    operations = [
        migrations.CreateModel(
            name='SepaExport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('xmldata', models.TextField()),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sepa_exports', to='pretixbase.Event')),
                ('orders', models.ManyToManyField(related_name='sepa_exports', to='pretixbase.Order')),
            ],
        ),
    ]
