import logging

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.notifications.crawlers import get_crawler
from apps.notifications.models import Notice, NoticeSource

logger = logging.getLogger(__name__)

_SOURCE = {
    'name': '데이콘 경진대회',
    'url': 'https://dacon.io/competitions',
    'crawler_type': 'dacon',
}


class Command(BaseCommand):
    help = '데이콘 경진대회 NoticeSource를 생성하고 현재 목록을 알림 없이 DB에 씨딩한다'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--chat-id',
            type=str,
            default='',
            help='알림을 발송할 텔레그램 채팅방 ID (미입력 시 기존 값 유지, 신규 생성 시 빈 값)',
        )

    def handle(self, *args, **options) -> None:
        source = self._ensure_source(options['chat_id'])
        count = self._seed_source(source)
        self.stdout.write(f'씨딩 완료: {count}건 저장')
        self.stdout.write('이제 check_new_notices 실행 시 새 대회만 알림이 발송됩니다.')

    def _ensure_source(self, chat_id: str) -> NoticeSource:
        source, created = NoticeSource.objects.get_or_create(
            name=_SOURCE['name'],
            defaults={
                'url': _SOURCE['url'],
                'crawler_type': _SOURCE['crawler_type'],
                'telegram_chat_id': chat_id,
                'is_active': True,
            },
        )
        if not created and chat_id and source.telegram_chat_id != chat_id:
            source.telegram_chat_id = chat_id
            source.save(update_fields=['telegram_chat_id'])
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
            raise CommandError(f'크롤러 오류: {e}') from e

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
                    'published_at': None,
                    'is_notified': True,
                },
            )
            if created:
                saved += 1

        self.stdout.write(f'{len(items)}건 수집 → {saved}건 신규 저장 (나머지는 이미 존재)')
        return saved
