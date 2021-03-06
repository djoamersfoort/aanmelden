# Generated by Django 3.0.6 on 2020-05-30 11:13

import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('src', '0003_auto_20200522_1532'),
    ]

    operations = [
        migrations.CreateModel(
            name='DjoUser',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AlterField(
            model_name='presence',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='src.DjoUser'),
        ),
    ]
