import logging

from django.core.management.base import BaseCommand

from apps.notifications.crawlers import get_crawler
from apps.notifications.models import Notice, NoticeSource

logger = logging.getLogger(__name__)

_SOURCE = {
    'name': '세종 비교과 프로그램',
    'url': 'https://do.sejong.ac.kr/ko/program/all/list/0/1?sort=date',
    'crawler_type': 'sejong_do',
}


class Command(BaseCommand):
    help = '두드림 비교과 프로그램 NoticeSource를 생성하고 현재 게시물을 알림 없이 DB에 씨딩한다'

    def handle(self, *args, **options) -> None:
        source = self._ensure_source()
        count = self._seed_source(source)
        self.stdout.write(f'씨딩 완료: {count}건 저장')
        self.stdout.write('이제 check_new_notices 실행 시 새 프로그램만 알림이 발송됩니다.')

    def _ensure_source(self) -> NoticeSource:
        source, created = NoticeSource.objects.get_or_create(
            name=_SOURCE['name'],
            defaults={
                'url': _SOURCE['url'],
                'crawler_type': _SOURCE['crawler_type'],
                'is_active': True,
            },
        )
        status = '생성' if created else '이미 존재'
        self.stdout.write(f'[{status}] {source.name}')
        return source

    def _seed_source(self, source: NoticeSource) -> int:
        self.stdout.write(f'[{source.name}] 크롤링 중...')
        try:
            crawler = get_crawler(source.crawler_type, source.url)
            items = crawler.crawl()
        except ValueError as e:
            logger.error('크롤러 생성 실패 (source=%s): %s', source.name, e)
            self.stderr.write(f'크롤러 오류: {e}')
            return 0

        if not items:
            self.stdout.write('수집된 항목 없음')
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

        self.stdout.write(f'{len(items)}건 수집 → {saved}건 신규 저장 (나머지는 이미 존재)')
        return saved
