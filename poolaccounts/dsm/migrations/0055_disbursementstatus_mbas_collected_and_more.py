# Generated by Django 4.2.11 on 2024-05-01 11:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0054_trasbasemodel_trasreceivables_traspayments'),
    ]

    operations = [
        migrations.AddField(
            model_name='disbursementstatus',
            name='mbas_collected',
            field=models.FloatField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='disbursementstatus',
            name='mbas_disbursed',
            field=models.FloatField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='disbursementstatus',
            name='reac',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AddField(
            model_name='disbursementstatus',
            name='reac_collected',
            field=models.FloatField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='disbursementstatus',
            name='reac_disbursed',
            field=models.FloatField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='disbursementstatus',
            name='sras_collected',
            field=models.FloatField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='disbursementstatus',
            name='sras_disbursed',
            field=models.FloatField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='disbursementstatus',
            name='tras_collected',
            field=models.FloatField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='disbursementstatus',
            name='tras_disbursed',
            field=models.FloatField(default=None, null=True),
        ),
    ]
