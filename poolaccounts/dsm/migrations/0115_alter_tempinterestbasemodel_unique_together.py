# Generated by Django 4.2.11 on 2024-06-27 12:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0114_alter_tempinterestbasemodel_unique_together'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='tempinterestbasemodel',
            unique_together={('Acc_type', 'Fin_year', 'Week_no', 'Entity')},
        ),
    ]
