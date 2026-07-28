from django.db import migrations

_ICON_BY_SLUG = {
    'library': '📚',
    'student': '🎓',
}


def seed_tool_icons(apps, schema_editor) -> None:
    Tool = apps.get_model('site', 'Tool')
    for slug, icon in _ICON_BY_SLUG.items():
        Tool.objects.filter(slug=slug).update(icon=icon)


def unseed_tool_icons(apps, schema_editor) -> None:
    Tool = apps.get_model('site', 'Tool')
    Tool.objects.filter(slug__in=_ICON_BY_SLUG.keys()).update(icon='')


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0003_tool_icon'),
    ]

    operations = [
        migrations.RunPython(seed_tool_icons, unseed_tool_icons),
    ]
