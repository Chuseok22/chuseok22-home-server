import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.crawlers import get_crawler
from apps.notifications.crawlers.github_trending import GithubTrendingDigestItem
from apps.notifications.models import Notice, NoticeSource
from apps.notifications.services.discord import DiscordService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'GitHub 트렌딩 TOP 10을 수집·요약해 Discord로 발송한다'

    def handle(self, *args: object, **options: object) -> None:
        source = NoticeSource.objects.filter(crawler_type='github_trending', is_active=True).first()
        if source is None:
            self.stdout.write('활성화된 github_trending NoticeSource가 없습니다.')
            return

        webhook_url = source.discord_webhook_url.strip()
        if not webhook_url:
            logger.warning('[%s] discord_webhook_url 미설정 — 알림 발송 건너뜀', source.name)
            self.stderr.write(f'[{source.name}] discord_webhook_url 미설정, 알림 건너뜀')
            return

        crawler = get_crawler(source.crawler_type, source.url)
        items = crawler.crawl()
        if not items:
            self.stdout.write('수집된 트렌딩 데이터 없음 (스크래핑 실패 가능성)')
            return

        item = items[0]
        if not isinstance(item, GithubTrendingDigestItem):
            logger.error('예상치 못한 아이템 타입: %s', type(item))
            return

        notice, created = Notice.objects.get_or_create(
            source=source, article_id=item.article_id,
            defaults={'title': item.title, 'url': item.url},
        )
        if not created and notice.is_notified:
            self.stdout.write('오늘 리포트는 이미 발송되었습니다.')
            return

        success = DiscordService().send_digest(webhook_url, item)
        if success:
            notice.is_notified = True
            notice.notified_at = timezone.now()
            notice.save(update_fields=['is_notified', 'notified_at'])
            self.stdout.write('GitHub 트렌딩 리포트 발송 완료')
        else:
            self.stderr.write('GitHub 트렌딩 리포트 발송 실패')
