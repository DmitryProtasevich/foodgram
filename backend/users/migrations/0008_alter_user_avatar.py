# Generated by Django 3.2.16 on 2025-06-08 16:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20250608_1227'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='avatar',
            field=models.ImageField(null=True, upload_to='users/%Y/%m/%d/', verbose_name='Аватар'),
        ),
    ]
