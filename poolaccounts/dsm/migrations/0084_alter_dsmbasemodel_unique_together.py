# Generated by Django 4.2.11 on 2024-05-30 11:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0083_alter_dsmbasemodel_unique_together'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='dsmbasemodel',
            unique_together={('Fin_year', 'Week_no', 'Entity', 'Revision_no')},
        ),
    ]
