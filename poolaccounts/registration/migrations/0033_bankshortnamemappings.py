# Generated by Django 4.2.11 on 2024-04-10 17:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0032_delete_bankstatement'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankShortNameMappings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('short_name', models.CharField(default=None, max_length=255)),
                ('end_date', models.DateField(default=None)),
                ('fin_code', models.CharField(default=None, max_length=255)),
            ],
            options={
                'db_table': 'short_name_mapping',
                'managed': True,
            },
        ),
    ]
