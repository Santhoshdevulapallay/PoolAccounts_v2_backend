# Generated by Django 4.2.11 on 2024-10-09 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0170_dsmbasemodel_legacy_dues'),
    ]

    operations = [
        migrations.AddField(
            model_name='congbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='mbasbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='netasbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='reacbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='scucbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='srasbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='trasbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
    ]
