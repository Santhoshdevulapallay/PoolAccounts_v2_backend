# Generated by Django 4.2.11 on 2024-04-22 10:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0040_disbursedentities_fin_code'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='disbursementstatus',
            unique_together={('Disbursed_date',)},
        ),
    ]
