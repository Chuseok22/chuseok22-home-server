import logging

from django.core.management.base import BaseCommand

from apps.notifications.crawlers import get_crawler
from apps.notifications.models import Notice, NoticeSource

logger = logging.getLogger(__name__)

_BASE = 'https://www.dreamspon.com'

# icon 값은 apps/notifications/migrations/0005_seed_notice_source_icons.py의
# _ICON_BY_NAME과 동일한 규칙을 따른다(신규 소스라 마이그레이션 파일에는 없음).
_SOURCES = [
    {'name': '일반장학금', 'url': f'{_BASE}/scholarship/list.html', 'icon': '💰'},
    {'name': '드림장학금', 'url': f'{_BASE}/dreamscholarship/list.html', 'icon': '🎁'},
]


class Command(BaseCommand):
    help = '드림스폰 장학금 NoticeSource를 생성하고 현재 목록을 알림 없이 DB에 씨딩한다'

    def handle(self, *args, **options) -> None:
        self.stdout.write('=== NoticeSource 생성 ===')
        sources = self._ensure_sources()

        self.stdout.write('\n=== 기존 항목 씨딩 (알림 미발송) ===')
        total = 0
        for source in sources:
            total += self._seed_source(source)

        self.stdout.write(f'\n씨딩 완료: 총 {total}건 저장')
        self.stdout.write('이제 check_new_notices 실행 시 새 장학금만 알림이 발송됩니다.')
        self.stdout.write('Discord 웹훅 URL은 Django Admin의 공지 출처 목록에서 각 소스에 설정하세요.')

    def _ensure_sources(self) -> list[NoticeSource]:
        sources = []
        for data in _SOURCES:
            source, created = NoticeSource.objects.get_or_create(
                name=data['name'],
                defaults={
                    'url': data['url'],
                    'crawler_type': 'dreamspon',
                    'icon': data['icon'],
                    'is_active': True,
                },
            )
            status = '생성' if created else '이미 존재'
            self.stdout.write(f'  [{status}] {source.name}')
            sources.append(source)
        return sources

    def _seed_source(self, source: NoticeSource) -> int:
        self.stdout.write(f'\n[{source.name}] 크롤링 중...')
        try:
            crawler = get_crawler(source.crawler_type, source.url)
            items = crawler.crawl()
        except ValueError as e:
            logger.error('크롤러 생성 실패 (source=%s): %s', source.name, e)
            self.stderr.write(f'  크롤러 오류: {e}')
            return 0

        if not items:
            self.stdout.write('  수집된 항목 없음')
            return 0

        saved = 0
        for item in items:
            _, created = Notice.objects.get_or_create(
                source=source,
                article_id=item.article_id,
                defaults={
                    'title': item.title,
                    'url': item.url,
                    'published_at': None,
                    'is_notified': True,
                },
            )
            if created:
                saved += 1

        self.stdout.write(f'  {len(items)}건 수집 → {saved}건 신규 저장 (나머지는 이미 존재)')
        return saved
