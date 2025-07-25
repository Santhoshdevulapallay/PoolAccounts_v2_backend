# Generated by Django 4.2.11 on 2024-11-28 12:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0174_remove_interestpayments_fin_code_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClosingBalances',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Month_year', models.CharField(default=None, max_length=15)),
                ('Fin_code', models.CharField(default=None, max_length=10)),
                ('Acc_type', models.CharField(default=None)),
                ('Closing_amount', models.FloatField(blank=True, default=None, null=True)),
            ],
            options={
                'db_table': 'closing_balances',
                'unique_together': {('Fin_code', 'Month_year', 'Acc_type')},
            },
        ),
    ]
