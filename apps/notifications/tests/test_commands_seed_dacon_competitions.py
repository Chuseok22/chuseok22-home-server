from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.notifications.crawlers.dacon import DaconItem
from apps.notifications.models import Notice, NoticeSource


class TestSeedDaconCompetitions(TestCase):
    def _run_with_items(self, items: list[DaconItem], chat_id: str | None = None) -> None:
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = items
        with patch(
            'apps.notifications.management.commands.seed_dacon_competitions.get_crawler',
            return_value=mock_crawler,
        ):
            if chat_id is None:
                call_command('seed_dacon_competitions', stdout=StringIO())
            else:
                call_command('seed_dacon_competitions', chat_id=chat_id, stdout=StringIO())

    def test_소스_생성_및_chat_id_저장(self) -> None:
        self._run_with_items([], chat_id='-100123456')
        source = NoticeSource.objects.get(name='데이콘 경진대회')
        self.assertEqual(source.crawler_type, 'dacon')
        self.assertEqual(source.url, 'https://dacon.io/competitions')
        self.assertEqual(source.telegram_chat_id, '-100123456')
        self.assertTrue(source.is_active)

    def test_기존_소스_chat_id_미전달시_보존(self) -> None:
        NoticeSource.objects.create(
            name='데이콘 경진대회',
            url='https://dacon.io/competitions',
            crawler_type='dacon',
            telegram_chat_id='-100existing',
            is_active=True,
        )
        self._run_with_items([])
        source = NoticeSource.objects.get(name='데이콘 경진대회')
        self.assertEqual(source.telegram_chat_id, '-100existing')

    def test_신규_항목_is_notified_true로_저장(self) -> None:
        item = DaconItem(
            article_id='236727',
            title='대회 제목',
            url='https://dacon.io/competitions/official/236727/overview/',
            status='참가신청중',
            participant_count=100,
            tags=['알고리즘'],
        )
        self._run_with_items([item], chat_id='-100123456')
        notice = Notice.objects.get(source__name='데이콘 경진대회', article_id='236727')
        self.assertTrue(notice.is_notified)
        self.assertEqual(notice.title, '대회 제목')
        self.assertIsNone(notice.published_at)

    def test_중복_항목_재저장_안함(self) -> None:
        item = DaconItem(
            article_id='236727', title='대회', url='https://dacon.io/x',
            status=None, participant_count=None, tags=[],
        )
        self._run_with_items([item], chat_id='-100123456')
        self._run_with_items([item], chat_id='-100123456')
        self.assertEqual(Notice.objects.filter(source__name='데이콘 경진대회').count(), 1)
