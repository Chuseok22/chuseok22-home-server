import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.crawlers import get_crawler
from apps.notifications.models import Notice, NoticeSource
from apps.notifications.services.telegram import TelegramService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '공지사항을 크롤링하고 새 글이 있으면 텔레그램 알림을 발송한다'

    def handle(self, *args, **options) -> None:
        sources = NoticeSource.objects.filter(is_active=True)
        if not sources.exists():
            self.stdout.write('활성화된 공지 출처가 없습니다.')
            return

        telegram = TelegramService()

        for source in sources:
            self.stdout.write(f'[{source.name}] 크롤링 시작')
            self._process_source(source, telegram)

    def _process_source(self, source: NoticeSource, telegram: TelegramService) -> None:
        try:
            crawler = get_crawler(source.crawler_type, source.url)
            items = crawler.crawl()
        except ValueError as e:
            logger.error('크롤러 생성 실패 (source=%s): %s', source.name, e)
            self.stderr.write(str(e))
            return

        if not items:
            self.stdout.write(f'[{source.name}] 수집된 항목 없음')
            return

        new_count = 0
        for item in items:
            notice, created = Notice.objects.get_or_create(
                source=source,
                article_id=item.article_id,
                defaults={
                    'title': item.title,
                    'url': item.url,
                    'published_at': item.published_at,
                },
            )

            if not created:
                continue

            new_count += 1
            success = telegram.send_notice(source, notice)
            if success:
                notice.is_notified = True
                notice.notified_at = timezone.now()
                notice.save(update_fields=['is_notified', 'notified_at'])
                self.stdout.write(f'  알림 발송 완료: {notice.title}')
            else:
                self.stderr.write(f'  알림 발송 실패: {notice.title}')

        self.stdout.write(f'[{source.name}] 신규 공지 {new_count}건 처리 완료')
