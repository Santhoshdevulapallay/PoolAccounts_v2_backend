# Generated by Django 4.2.11 on 2024-05-03 12:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0056_disbursedentities_is_prevweeks'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='disbursementstatus',
            name='dsm_disbursed',
        ),
        migrations.RemoveField(
            model_name='disbursementstatus',
            name='mbas_disbursed',
        ),
        migrations.RemoveField(
            model_name='disbursementstatus',
            name='reac_disbursed',
        ),
        migrations.RemoveField(
            model_name='disbursementstatus',
            name='sras_disbursed',
        ),
        migrations.RemoveField(
            model_name='disbursementstatus',
            name='tras_disbursed',
        ),
    ]
