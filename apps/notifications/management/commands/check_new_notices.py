import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.crawlers import get_crawler
from apps.notifications.crawlers.base import BaseNoticeItem
from apps.notifications.crawlers.linkareer import ContestItem
from apps.notifications.crawlers.sejong import SejongNoticeItem
from apps.notifications.crawlers.sejong_do import SejongDoItem
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
        if not source.telegram_chat_id:
            logger.warning('[%s] telegram_chat_id 미설정 — 알림 발송 건너뜀', source.name)
            self.stderr.write(f'[{source.name}] telegram_chat_id 미설정, 알림 건너뜀')
            return

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
            published_at = self._get_published_at(item)
            notice, created = Notice.objects.get_or_create(
                source=source,
                article_id=item.article_id,
                defaults={
                    'title': item.title,
                    'url': item.url,
                    'published_at': published_at,
                },
            )

            if not created and notice.is_notified:
                continue

            # 상세 크롤링 지원 시 신규 항목만 추가 요청
            detail = crawler.crawl_detail(item.url)
            final_item = detail if detail is not None else item

            new_count += 1
            success = telegram.send_notice(source.telegram_chat_id, source, final_item)
            if success:
                notice.is_notified = True
                notice.notified_at = timezone.now()
                notice.save(update_fields=['is_notified', 'notified_at'])
                self.stdout.write(f'  알림 발송 완료: {notice.title}')
            else:
                self.stderr.write(f'  알림 발송 실패: {notice.title}')

        self.stdout.write(f'[{source.name}] 신규 공지 {new_count}건 처리 완료')

    def _get_published_at(self, item: BaseNoticeItem) -> date | None:
        """아이템 타입에 따라 Notice.published_at에 저장할 날짜를 반환한다."""
        if isinstance(item, SejongNoticeItem):
            return item.published_at
        if isinstance(item, SejongDoItem):
            return item.operation_start.date() if item.operation_start else None
        if isinstance(item, ContestItem):
            return item.application_end
        return None
