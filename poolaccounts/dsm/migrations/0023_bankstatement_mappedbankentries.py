# Generated by Django 4.2.11 on 2024-03-27 11:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0022_temporarymatched_is_infirm'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankStatement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ValueDate', models.DateField(default=None)),
                ('PostDate', models.DateField(default=None)),
                ('Description', models.CharField(blank=True, default=None, max_length=400, null=True)),
                ('Debit', models.FloatField(blank=True, default=None, null=True)),
                ('Credit', models.FloatField(blank=True, default=None, null=True)),
                ('Balance', models.FloatField(blank=True, default=None, null=True)),
                ('IsMapped', models.BooleanField(default=None)),
            ],
            options={
                'db_table': 'bank_statement',
                'unique_together': {('ValueDate', 'Description', 'Credit')},
            },
        ),
        migrations.CreateModel(
            name='MappedBankEntries',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Pool_Acc', models.CharField(default=None, max_length=15)),
                ('Fin_year', models.CharField(blank=True, default=None, max_length=10, null=True)),
                ('Week_no', models.IntegerField(blank=True, default=None, null=True)),
                ('Amount', models.FloatField(default=None)),
                ('Other_info', models.TextField(default=None)),
                ('ValueDate_fk', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='dsm.bankstatement')),
            ],
            options={
                'db_table': 'mapped_bankentries',
            },
        ),
    ]
