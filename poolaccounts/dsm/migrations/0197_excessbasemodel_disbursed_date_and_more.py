# Generated by Django 4.2.11 on 2025-06-13 16:39

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0196_alter_excessbasemodel_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='excessbasemodel',
            name='Disbursed_date',
            field=models.DateField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name='reconuploadstatus',
            name='Admin_uploaded_time',
            field=models.DateTimeField(default=datetime.datetime(2025, 6, 13, 16, 39, 11, 122613)),
        ),
        migrations.AlterField(
            model_name='reconuploadstatus',
            name='Uploaded_time',
            field=models.DateTimeField(default=datetime.datetime(2025, 6, 13, 16, 39, 11, 122613)),
        ),
    ]
