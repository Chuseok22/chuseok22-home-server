from django.db import migrations


def seed_lecture_tool(apps, schema_editor) -> None:
    Tool = apps.get_model('site', 'Tool')
    Tool.objects.get_or_create(
        slug='lecture',
        defaults={
            'title': '강의 다운로드',
            'description': '집현캠퍼스 강의 영상 다운로드',
            'icon': '🎬',
            'is_owner_only': True,
            'url_name': 'site:lab-lecture',
            'order': 3,
        },
    )


def remove_lecture_tool(apps, schema_editor) -> None:
    Tool = apps.get_model('site', 'Tool')
    Tool.objects.filter(slug='lecture').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('site', '0004_seed_tool_icons'),
    ]

    operations = [
        migrations.RunPython(seed_lecture_tool, remove_lecture_tool),
    ]
