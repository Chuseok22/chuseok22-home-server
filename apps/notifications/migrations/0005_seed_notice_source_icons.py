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
    NoticeSource = apps.get_model('notifications', 'NoticeSource')
    for name, icon in _ICON_BY_NAME.items():
        NoticeSource.objects.filter(name=name).update(icon=icon)


def unseed_notice_source_icons(apps, schema_editor) -> None:
    NoticeSource = apps.get_model('notifications', 'NoticeSource')
    NoticeSource.objects.filter(name__in=_ICON_BY_NAME.keys()).update(icon='')


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_noticesource_icon'),
    ]

    operations = [
        migrations.RunPython(seed_notice_source_icons, unseed_notice_source_icons),
    ]
