# Generated by Django 3.0.6 on 2020-06-10 10:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0004_auto_20200530_1313'),
    ]

    operations = [
        migrations.AddField(
            model_name='presence',
            name='seen',
            field=models.BooleanField(default=False),
        ),
    ]