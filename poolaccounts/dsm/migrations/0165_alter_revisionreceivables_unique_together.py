# Generated by Django 4.2.11 on 2024-08-26 15:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0164_disbursementstatus_revision_disbursed'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='revisionreceivables',
            unique_together={('Disbursed_amount', 'rcvstatus_fk', 'disbursed_date')},
        ),
    ]
