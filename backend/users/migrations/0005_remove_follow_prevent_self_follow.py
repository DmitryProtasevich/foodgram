# Generated by Django 3.2.16 on 2025-06-06 08:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20250606_1115'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='follow',
            name='prevent_self_follow',
        ),
    ]
