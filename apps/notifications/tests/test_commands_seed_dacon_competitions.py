from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.notifications.crawlers.dacon import DaconItem
from apps.notifications.models import Notice, NoticeSource


class TestSeedDaconCompetitions(TestCase):
    def _run_with_items(self, items: list[DaconItem], webhook_url: str | None = None) -> None:
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = items
        with patch(
            'apps.notifications.management.commands.seed_dacon_competitions.get_crawler',
            return_value=mock_crawler,
        ):
            if webhook_url is None:
                call_command('seed_dacon_competitions', stdout=StringIO())
            else:
                call_command('seed_dacon_competitions', webhook_url=webhook_url, stdout=StringIO())

    def test_소스_생성_및_webhook_url_저장(self) -> None:
        self._run_with_items([], webhook_url='https://discord.com/api/webhooks/1/new')
        source = NoticeSource.objects.get(name='데이콘 경진대회')
        self.assertEqual(source.crawler_type, 'dacon')
        self.assertEqual(source.url, 'https://dacon.io/competitions')
        self.assertEqual(source.discord_webhook_url, 'https://discord.com/api/webhooks/1/new')
        self.assertTrue(source.is_active)

    def test_기존_소스_webhook_url_미전달시_보존(self) -> None:
        NoticeSource.objects.create(
            name='데이콘 경진대회',
            url='https://dacon.io/competitions',
            crawler_type='dacon',
            discord_webhook_url='https://discord.com/api/webhooks/1/existing',
            is_active=True,
        )
        self._run_with_items([])
        source = NoticeSource.objects.get(name='데이콘 경진대회')
        self.assertEqual(source.discord_webhook_url, 'https://discord.com/api/webhooks/1/existing')

    def test_신규_항목_is_notified_true로_저장(self) -> None:
        item = DaconItem(
            article_id='236727',
            title='대회 제목',
            url='https://dacon.io/competitions/official/236727/overview/',
            status='참가신청중',
            participant_count=100,
            tags=['알고리즘'],
        )
        self._run_with_items([item], webhook_url='https://discord.com/api/webhooks/1/new')
        notice = Notice.objects.get(source__name='데이콘 경진대회', article_id='236727')
        self.assertTrue(notice.is_notified)
        self.assertEqual(notice.title, '대회 제목')
        self.assertIsNone(notice.published_at)

    def test_중복_항목_재저장_안함(self) -> None:
        item = DaconItem(
            article_id='236727', title='대회', url='https://dacon.io/x',
            status=None, participant_count=None, tags=[],
        )
        self._run_with_items([item], webhook_url='https://discord.com/api/webhooks/1/new')
        self._run_with_items([item], webhook_url='https://discord.com/api/webhooks/1/new')
        self.assertEqual(Notice.objects.filter(source__name='데이콘 경진대회').count(), 1)
