# Generated by Django 4.2.9 on 2024-02-20 12:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0017_registration_id_alter_registration_fin_code_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='registration',
            unique_together=None,
        ),
        migrations.DeleteModel(
            name='BankDetails',
        ),
        migrations.DeleteModel(
            name='Registration',
        ),
    ]
