from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.notifications.crawlers.sejong_do import SejongDoItem
from apps.notifications.models import NoticeSource


class TestSeedDoPrograms(TestCase):
    def _run_with_items(self, items: list[SejongDoItem]) -> None:
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = items
        with patch(
            'apps.notifications.management.commands.seed_do_programs.get_crawler',
            return_value=mock_crawler,
        ):
            call_command('seed_do_programs', stdout=StringIO())

    def test_소스_생성시_icon_기본값_저장(self) -> None:
        self._run_with_items([])
        source = NoticeSource.objects.get(name='세종 비교과 프로그램')
        self.assertEqual(source.crawler_type, 'sejong_do')
        self.assertTrue(source.is_active)
        self.assertEqual(source.icon, '🗓️')

    def test_기존_소스_재실행시_admin에서_수정한_icon_보존(self) -> None:
        NoticeSource.objects.create(
            name='세종 비교과 프로그램',
            url='https://do.sejong.ac.kr/ko/program/all/list/0/1?sort=date',
            crawler_type='sejong_do',
            icon='📖',
            is_active=True,
        )
        self._run_with_items([])
        source = NoticeSource.objects.get(name='세종 비교과 프로그램')
        self.assertEqual(source.icon, '📖')
