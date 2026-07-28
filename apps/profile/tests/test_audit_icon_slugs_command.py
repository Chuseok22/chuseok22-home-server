import pytest
from django.core.management import call_command
from django.db import connection

from apps.profile.models import Skill


@pytest.mark.django_db
def test_audit_icon_slugs는_유효하지_않은_슬러그를_가진_레코드를_출력한다(capsys: pytest.CaptureFixture) -> None:
    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', icon_slug='django', order=0)
    # Skill.save()의 검증은 icon_slug가 "바뀔 때만" 걸리므로, 검증 도입 이전에 이미 저장된
    # 잘못된 데이터를 재현하려면 save()를 거치지 않는 raw SQL로 직접 삽입해야 한다.
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO profile_skill (category, name, icon_slug, "order") VALUES (%s, %s, %s, %s)',
            [Skill.Category.INFRA, 'Java(레거시)', 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/java/java-original.svg', 1],
        )

    call_command('audit_icon_slugs')

    output = capsys.readouterr().out
    assert 'Java(레거시)' in output
    assert 'Django' not in output


@pytest.mark.django_db
def test_audit_icon_slugs는_문제가_없으면_안내_메시지를_출력한다(capsys: pytest.CaptureFixture) -> None:
    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', icon_slug='django', order=0)

    call_command('audit_icon_slugs')

    output = capsys.readouterr().out
    assert '문제 없음' in output
