from django.db import migrations


def seed_tools(apps, schema_editor) -> None:
    Tool = apps.get_model('site', 'Tool')
    Tool.objects.get_or_create(
        slug='library',
        defaults={
            'title': '스터디룸 예약',
            'description': '학술정보원 스터디룸 예약 현황 조회 및 예약',
            'is_owner_only': True,
            'url_name': 'site:lab-library',
            'order': 1,
        },
    )
    Tool.objects.get_or_create(
        slug='student',
        defaults={
            'title': '학생 조회',
            'description': '세종대학교 Classic 시스템 학생 정보 조회',
            'is_owner_only': True,
            'url_name': 'site:lab-student',
            'order': 2,
        },
    )


def remove_tools(apps, schema_editor) -> None:
    Tool = apps.get_model('site', 'Tool')
    Tool.objects.filter(slug__in=['library', 'student']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('site', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_tools, remove_tools),
    ]
