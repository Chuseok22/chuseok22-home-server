from django.db import migrations

_ICON_BY_SLUG = {
    'library': '📚',
    'student': '🎓',
}


def seed_tool_icons(apps, schema_editor) -> None:
    # icon이 비어있는 로우만 채운다 — 마이그레이션을 되돌렸다 다시 적용하는 사이 Admin에서
    # 아이콘을 수정했다면 그 값을 덮어쓰지 않는다.
    Tool = apps.get_model('site', 'Tool')
    for slug, icon in _ICON_BY_SLUG.items():
        Tool.objects.filter(slug=slug, icon='').update(icon=icon)


def unseed_tool_icons(apps, schema_editor) -> None:
    # 현재 값이 이 마이그레이션이 채운 값과 같을 때만 되돌린다 — Admin에서 그 사이 다른
    # 값으로 바꿔뒀다면 롤백으로 지우지 않는다.
    Tool = apps.get_model('site', 'Tool')
    for slug, icon in _ICON_BY_SLUG.items():
        Tool.objects.filter(slug=slug, icon=icon).update(icon='')


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0003_tool_icon'),
    ]

    operations = [
        migrations.RunPython(seed_tool_icons, unseed_tool_icons),
    ]
