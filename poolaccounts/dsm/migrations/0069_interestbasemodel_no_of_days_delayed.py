# Generated by Django 4.2.11 on 2024-05-14 16:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0068_interestbasemodel_paid_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='interestbasemodel',
            name='No_of_days_delayed',
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
    ]
