# Generated by Django 4.0.7 on 2022-11-25 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0018_specialdate_announcement'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userinfo',
            name='age',
        ),
        migrations.AddField(
            model_name='userinfo',
            name='account_type',
            field=models.CharField(default='', max_length=100),
        ),
    ]