# Generated by Django 4.1.4 on 2022-12-29 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_InitialData'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imagejob',
            name='status',
            field=models.CharField(default='IN QUEUE', max_length=30),
        ),
        migrations.AlterField(
            model_name='imagejob',
            name='test_result',
            field=models.BooleanField(blank=True, default=False),
        ),
    ]