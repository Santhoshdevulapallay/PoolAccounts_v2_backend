# Generated by Django 4.2.11 on 2024-08-26 11:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dsm', '0160_disbursementstatus_cong_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RevisionReceivables',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Disbursed_amount', models.FloatField(blank=True, null=True)),
                ('iom_date', models.DateField(blank=True, default=None, null=True)),
                ('disbursed_date', models.DateField(blank=True, default=None, null=True)),
                ('neft_txnno', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('rcvstatus_fk', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='dsm.revisionbasemodel')),
            ],
            options={
                'db_table': 'revision_receivables',
            },
        ),
    ]
