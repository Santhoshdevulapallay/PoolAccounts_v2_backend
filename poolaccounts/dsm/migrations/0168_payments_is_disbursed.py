# Generated by Django 4.2.11 on 2024-10-08 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0167_excessbasemodel_acc_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='payments',
            name='Is_disbursed',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
