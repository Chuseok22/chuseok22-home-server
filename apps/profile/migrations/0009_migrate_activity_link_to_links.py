from django.db import migrations


def migrate_link_to_links(apps, schema_editor) -> None:
    Activity = apps.get_model('profile', 'Activity')
    for activity in Activity.objects.exclude(link=''):
        activity.links = [{'type': 'official', 'url': activity.link}]
        activity.save(update_fields=['links'])


def noop_reverse(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0008_activityattachment'),
    ]

    operations = [
        migrations.RunPython(migrate_link_to_links, noop_reverse),
    ]
