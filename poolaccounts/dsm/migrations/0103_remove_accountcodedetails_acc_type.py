# Generated by Django 4.2.11 on 2024-06-20 16:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0102_accountcodedetails'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accountcodedetails',
            name='acc_type',
        ),
    ]
