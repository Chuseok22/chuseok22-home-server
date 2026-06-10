import logging

from django.core.management.base import BaseCommand

from apps.notifications.crawlers import get_crawler
from apps.notifications.models import Notice, NoticeSource

logger = logging.getLogger(__name__)

_BASE = 'https://www.sejong.ac.kr/kor/intro'
_QUERY = '?mode=list&article.offset=0&articleLimit=10'

_SOURCES = [
    {'name': '일반공지', 'url': f'{_BASE}/notice1.do{_QUERY}'},
    {'name': '학사공지', 'url': f'{_BASE}/notice3.do{_QUERY}'},
    {'name': '국제교류', 'url': f'{_BASE}/notice4.do{_QUERY}'},
    {'name': '취업',    'url': f'{_BASE}/notice6.do{_QUERY}'},
    {'name': '장학',    'url': f'{_BASE}/notice7.do{_QUERY}'},
    {'name': '채용모집', 'url': f'{_BASE}/notice8.do{_QUERY}'},
]


class Command(BaseCommand):
    help = 'NoticeSource를 생성하고 현재 게시물을 알림 없이 DB에 씨딩한다'

    def handle(self, *args, **options) -> None:
        self.stdout.write('=== NoticeSource 생성 ===')
        sources = self._ensure_sources()

        self.stdout.write('\n=== 기존 게시물 씨딩 (알림 미발송) ===')
        total = 0
        for source in sources:
            count = self._seed_source(source)
            total += count

        self.stdout.write(f'\n씨딩 완료: 총 {total}건 저장')
        self.stdout.write('이제 check_new_notices 실행 시 새 글만 알림이 발송됩니다.')

    def _ensure_sources(self) -> list[NoticeSource]:
        sources = []
        for data in _SOURCES:
            source, created = NoticeSource.objects.get_or_create(
                name=data['name'],
                defaults={
                    'url': data['url'],
                    'crawler_type': 'sejong',
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
            self.stdout.write(f'  수집된 항목 없음')
            return 0

        saved = 0
        for item in items:
            _, created = Notice.objects.get_or_create(
                source=source,
                article_id=item.article_id,
                defaults={
                    'title': item.title,
                    'url': item.url,
                    'published_at': item.published_at,
                    'is_notified': True,  # 알림 없이 이미 처리된 것으로 표시
                },
            )
            if created:
                saved += 1

        self.stdout.write(f'  {len(items)}건 수집 → {saved}건 신규 저장 (나머지는 이미 존재)')
        return saved
