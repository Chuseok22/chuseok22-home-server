from django.db import migrations


def migrate_link_to_links(apps, schema_editor) -> None:
    Activity = apps.get_model('profile', 'Activity')
    for activity in Activity.objects.exclude(link=''):
        activity.links = [{'type': 'official', 'url': activity.link}]
        activity.save(update_fields=['links'])


def restore_link_from_links(apps, schema_editor) -> None:
    # official 타입 링크가 있으면 그걸, 없으면 첫 번째 링크를 복원한다(둘 다 없으면 빈 문자열
    # 그대로 둔다). links는 여러 개를 담을 수 있어 원래 단일 link로 완전히 역변환할 수는
    # 없지만, 최소한 대표 링크 하나는 롤백 시에도 유지되도록 하는 정책이다.
    Activity = apps.get_model('profile', 'Activity')
    for activity in Activity.objects.exclude(links=[]):
        official = next((link['url'] for link in activity.links if link.get('type') == 'official'), None)
        activity.link = official or activity.links[0].get('url', '')
        activity.save(update_fields=['link'])


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0008_activityattachment'),
    ]

    operations = [
        migrations.RunPython(migrate_link_to_links, restore_link_from_links),
    ]
