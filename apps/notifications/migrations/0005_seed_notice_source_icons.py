from django.db import migrations

_ICON_BY_NAME = {
    '일반공지': '📌',
    '학사공지': '🎓',
    '국제교류': '🌐',
    '취업': '💼',
    '장학': '💰',
    '채용모집': '📋',
    '데이콘 경진대회': '🏆',
    '세종 비교과 프로그램': '🗓️',
}


def seed_notice_source_icons(apps, schema_editor) -> None:
    # icon이 비어있는 로우만 채운다 — 마이그레이션을 되돌렸다 다시 적용하는 사이 Admin에서
    # 아이콘을 수정했다면 그 값을 덮어쓰지 않는다.
    NoticeSource = apps.get_model('notifications', 'NoticeSource')
    for name, icon in _ICON_BY_NAME.items():
        NoticeSource.objects.filter(name=name, icon='').update(icon=icon)


def unseed_notice_source_icons(apps, schema_editor) -> None:
    # 현재 값이 이 마이그레이션이 채운 값과 같을 때만 되돌린다 — Admin에서 그 사이 다른
    # 값으로 바꿔뒀다면 롤백으로 지우지 않는다.
    NoticeSource = apps.get_model('notifications', 'NoticeSource')
    for name, icon in _ICON_BY_NAME.items():
        NoticeSource.objects.filter(name=name, icon=icon).update(icon='')


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_noticesource_icon'),
    ]

    operations = [
        migrations.RunPython(seed_notice_source_icons, unseed_notice_source_icons),
    ]
