from django.core.management.base import BaseCommand

from apps.clubs.models import TrackedClub

# SOPT(sopt.org)는 정적 요청으로 본문을 가져올 수 없는 React SPA로 확인돼(구현 착수 전 WebFetch
# 검증 결과) 이번 시딩에서 제외한다 — 스펙의 "위험 요소"에 정리된 대로, SPA로 확인된 소스만
# 예외 처리하고 나머지 설계는 바꾸지 않는다. 헤드리스 렌더링 도입 여부를 별도로 논의한 뒤 추가한다.
_INITIAL_CLUBS = [
    ('YAPP', 'https://www.yapp.co.kr/recruit'),
    ('NEXTERS', 'https://nexters.co.kr/'),
    ('Mash-Up', 'https://mash-up.kr/'),
]


class Command(BaseCommand):
    help = (
        '초기 감시 대상 동아리 3곳(YAPP/NEXTERS/Mash-Up)을 시딩한다. SOPT는 SPA라 이번 시딩에서 '
        '제외했다(위 _INITIAL_CLUBS 주석 참고). discord_webhook_url은 비워둔 채 생성하므로, 실행 후 '
        'Admin에서 각 동아리의 웹훅 URL을 채워야 알림이 발송된다.'
    )

    def handle(self, *args: object, **options: object) -> None:
        created_count = 0
        for name, homepage_url in _INITIAL_CLUBS:
            _club, created = TrackedClub.objects.get_or_create(
                name=name, defaults={'homepage_url': homepage_url},
            )
            if created:
                created_count += 1
                self.stdout.write(f'[생성] {name} ({homepage_url})')
            else:
                self.stdout.write(f'[건너뜀] {name} 이미 존재')
        self.stdout.write(f'총 {created_count}건 생성됨. Admin에서 각 동아리의 Discord 웹훅 URL을 입력해주세요.')
