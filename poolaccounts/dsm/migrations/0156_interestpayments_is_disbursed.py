# Generated by Django 4.2.11 on 2024-08-07 10:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0155_congbasemodel_congreceivables_congpayments'),
    ]

    operations = [
        migrations.AddField(
            model_name='interestpayments',
            name='Is_disbursed',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
