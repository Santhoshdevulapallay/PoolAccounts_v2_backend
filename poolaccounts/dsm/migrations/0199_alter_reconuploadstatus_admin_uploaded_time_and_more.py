# Generated by Django 4.2.11 on 2025-06-13 16:45

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0198_alter_reconuploadstatus_admin_uploaded_time_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reconuploadstatus',
            name='Admin_uploaded_time',
            field=models.DateTimeField(default=datetime.datetime(2025, 6, 13, 16, 45, 20, 700944)),
        ),
        migrations.AlterField(
            model_name='reconuploadstatus',
            name='Uploaded_time',
            field=models.DateTimeField(default=datetime.datetime(2025, 6, 13, 16, 45, 20, 700944)),
        ),
    ]
