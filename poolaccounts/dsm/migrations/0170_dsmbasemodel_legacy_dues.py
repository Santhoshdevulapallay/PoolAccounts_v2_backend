# Generated by Django 4.2.11 on 2024-10-09 10:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0169_congpayments_is_disbursed_irpayments_is_disbursed_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dsmbasemodel',
            name='Legacy_dues',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
    ]
