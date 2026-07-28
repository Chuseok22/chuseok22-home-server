from django.core.management.base import BaseCommand

from apps.core.icons import is_valid_icon_slug
from apps.profile.models import Skill


class Command(BaseCommand):
    help = (
        'Skill.icon_slug 중 벤더링된 아이콘 세트(Simple Icons/other-brands)에 없는 값을 가진 '
        '레코드를 읽기 전용으로 나열한다. DB를 변경하지 않는다.'
    )

    def handle(self, *args, **options) -> None:
        invalid_skills = [
            skill
            for skill in Skill.objects.exclude(icon_slug='')
            if not is_valid_icon_slug(skill.icon_slug)
        ]

        if not invalid_skills:
            self.stdout.write(self.style.SUCCESS('문제 없음 — 모든 Skill.icon_slug가 벤더링된 세트에 존재합니다.'))
            return

        self.stdout.write(self.style.WARNING(f'{len(invalid_skills)}건의 유효하지 않은 icon_slug 발견:'))
        for skill in invalid_skills:
            self.stdout.write(f'  - [{skill.pk}] {skill.name}: {skill.icon_slug!r}')
        self.stdout.write(
            'Admin에서 각 레코드의 icon_slug를 벤더링된 슬러그로 수정하거나, '
            'other-brands에 해당 브랜드를 벤더링한 뒤 슬러그를 갱신하세요.'
        )
