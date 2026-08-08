from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.notifications.crawlers.github_trending import GithubTrendingDigestItem, TrendingRepoEntry
from apps.notifications.models import Notice, NoticeSource

_REPO = TrendingRepoEntry(
    owner_repo='owner/repo', url='https://github.com/owner/repo',
    language='Python', stars_today=100, total_stars=1000, total_forks=50,
    summary_ko='요약',
)
_DIGEST_ITEM = GithubTrendingDigestItem(
    article_id='2026-08-08',
    title='GitHub 트렌딩 TOP 1 (2026.08.08)',
    url='https://github.com/trending?since=daily',
    repos=[_REPO],
)


class TestSendGithubTrendingReportCommand(TestCase):
    def test_활성_소스_없으면_조용히_종료(self) -> None:
        out = StringIO()
        call_command('send_github_trending_report', stdout=out)
        self.assertIn('활성화된', out.getvalue())
        self.assertEqual(Notice.objects.count(), 0)

    def test_웹훅_url_미설정시_건너뜀(self) -> None:
        NoticeSource.objects.create(
            name='GitHub 트렌딩', url='https://github.com/trending?since=daily',
            crawler_type='github_trending', discord_webhook_url='', is_active=True,
        )
        err = StringIO()
        call_command('send_github_trending_report', stderr=err)
        self.assertIn('discord_webhook_url', err.getvalue())
        self.assertEqual(Notice.objects.count(), 0)

    def test_비활성_소스는_처리_대상에서_제외(self) -> None:
        NoticeSource.objects.create(
            name='GitHub 트렌딩', url='https://github.com/trending?since=daily',
            crawler_type='github_trending',
            discord_webhook_url='https://discord.com/api/webhooks/1/a', is_active=False,
        )
        out = StringIO()
        call_command('send_github_trending_report', stdout=out)
        self.assertIn('활성화된', out.getvalue())
        self.assertEqual(Notice.objects.count(), 0)

    @patch('apps.notifications.management.commands.send_github_trending_report.get_crawler')
    @patch('apps.notifications.management.commands.send_github_trending_report.DiscordService')
    def test_정상_흐름_notice_생성_및_is_notified_true(self, mock_discord_cls, mock_get_crawler) -> None:
        source = NoticeSource.objects.create(
            name='GitHub 트렌딩', url='https://github.com/trending?since=daily',
            crawler_type='github_trending',
            discord_webhook_url='https://discord.com/api/webhooks/1/a', is_active=True,
        )
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = [_DIGEST_ITEM]
        mock_get_crawler.return_value = mock_crawler
        mock_discord_cls.return_value.send_digest.return_value = True

        call_command('send_github_trending_report', stdout=StringIO())

        notice = Notice.objects.get(source=source, article_id='2026-08-08')
        self.assertTrue(notice.is_notified)
        self.assertIsNotNone(notice.notified_at)
        mock_discord_cls.return_value.send_digest.assert_called_once_with(
            'https://discord.com/api/webhooks/1/a', _DIGEST_ITEM,
        )

    @patch('apps.notifications.management.commands.send_github_trending_report.get_crawler')
    def test_크롤러가_빈_리스트_반환하면_notice_생성_안됨(self, mock_get_crawler) -> None:
        NoticeSource.objects.create(
            name='GitHub 트렌딩', url='https://github.com/trending?since=daily',
            crawler_type='github_trending',
            discord_webhook_url='https://discord.com/api/webhooks/1/a', is_active=True,
        )
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = []
        mock_get_crawler.return_value = mock_crawler

        call_command('send_github_trending_report', stdout=StringIO())

        self.assertEqual(Notice.objects.count(), 0)

    @patch('apps.notifications.management.commands.send_github_trending_report.get_crawler')
    @patch('apps.notifications.management.commands.send_github_trending_report.DiscordService')
    def test_같은_날_이미_발송됐으면_재발송_안함(self, mock_discord_cls, mock_get_crawler) -> None:
        source = NoticeSource.objects.create(
            name='GitHub 트렌딩', url='https://github.com/trending?since=daily',
            crawler_type='github_trending',
            discord_webhook_url='https://discord.com/api/webhooks/1/a', is_active=True,
        )
        Notice.objects.create(
            source=source, article_id='2026-08-08', title='기존 제목',
            url='https://github.com/trending?since=daily', is_notified=True,
        )
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = [_DIGEST_ITEM]
        mock_get_crawler.return_value = mock_crawler

        call_command('send_github_trending_report', stdout=StringIO())

        mock_discord_cls.return_value.send_digest.assert_not_called()

    @patch('apps.notifications.management.commands.send_github_trending_report.get_crawler')
    @patch('apps.notifications.management.commands.send_github_trending_report.DiscordService')
    def test_discord_발송_실패시_is_notified_유지(self, mock_discord_cls, mock_get_crawler) -> None:
        NoticeSource.objects.create(
            name='GitHub 트렌딩', url='https://github.com/trending?since=daily',
            crawler_type='github_trending',
            discord_webhook_url='https://discord.com/api/webhooks/1/a', is_active=True,
        )
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = [_DIGEST_ITEM]
        mock_get_crawler.return_value = mock_crawler
        mock_discord_cls.return_value.send_digest.return_value = False

        call_command('send_github_trending_report', stderr=StringIO())

        notice = Notice.objects.get(article_id='2026-08-08')
        self.assertFalse(notice.is_notified)
