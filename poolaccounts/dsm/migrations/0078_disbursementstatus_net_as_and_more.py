# Generated by Django 4.2.11 on 2024-05-27 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0077_remove_netasbasemodel_reac_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='disbursementstatus',
            name='net_as',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AddField(
            model_name='disbursementstatus',
            name='net_as_prevwk',
            field=models.BooleanField(default=False, null=True),
        ),
    ]
