# Generated by Django 4.2.11 on 2024-04-16 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0035_bankshortnamemappings_is_ib_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DueDates',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pool_acc', models.CharField(default=None, max_length=50)),
                ('days', models.IntegerField(default=None)),
                ('start_date', models.DateField(default=None)),
                ('end_date', models.DateField(blank=True, default=None, null=True)),
            ],
            options={
                'db_table': 'due_dates',
                'managed': True,
            },
        ),
    ]
