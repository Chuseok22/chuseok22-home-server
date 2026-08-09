from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0009_migrate_activity_link_to_links'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='activity',
            name='link',
        ),
    ]
