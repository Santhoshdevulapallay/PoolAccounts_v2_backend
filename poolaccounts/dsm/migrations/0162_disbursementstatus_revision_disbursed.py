# Generated by Django 4.2.11 on 2024-08-26 15:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0161_revisionreceivables'),
    ]

    operations = [
        migrations.AddField(
            model_name='disbursementstatus',
            name='revision_disbursed',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
