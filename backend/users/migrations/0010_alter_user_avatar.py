# Generated by Django 3.2.16 on 2025-06-08 17:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_user_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='users/%Y/%m/%d/', verbose_name='Аватар'),
        ),
    ]
