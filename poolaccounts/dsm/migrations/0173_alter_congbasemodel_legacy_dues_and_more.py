# Generated by Django 4.2.11 on 2024-10-10 15:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0172_alter_dsmbasemodel_legacy_dues'),
    ]

    operations = [
        migrations.AlterField(
            model_name='congbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='mbasbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='netasbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='reacbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='scucbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='srasbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='trasbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(default=False),
        ),
    ]
