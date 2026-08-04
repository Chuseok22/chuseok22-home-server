from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.notifications.crawlers.dacon import DaconItem
from apps.notifications.crawlers.dreamspon import DreamsponItem
from apps.notifications.management.commands.check_new_notices import Command
from apps.notifications.models import Notice, NoticeSource


class TestCheckNewNoticesGetPublishedAt(TestCase):
    def setUp(self) -> None:
        self.command = Command()

    def test_dacon_아이템은_게시일_없음(self) -> None:
        item = DaconItem(
            article_id='236727',
            title='대회 제목',
            url='https://dacon.io/competitions/official/236727/overview/',
            status='참가신청중',
            participant_count=100,
            tags=[],
        )
        result = self.command._get_published_at(item)
        self.assertIsNone(result)

    def test_dreamspon_아이템은_신청_마감일이_게시일(self) -> None:
        item = DreamsponItem(
            article_id='9130', title='장학금', url='https://www.dreamspon.com/scholarship/view.html?idx=9130',
            organization='에디티지', hit_count=1294, scholarship_type='포상/상금',
            target='대학생', recruit_count='총 16명', benefit='최대 1,000만원',
            application_start=date(2026, 5, 26), application_end=date(2026, 8, 7), tags=[],
        )
        result = self.command._get_published_at(item)
        self.assertEqual(result, date(2026, 8, 7))


class TestCheckNewNoticesProcessSource(TestCase):
    def setUp(self) -> None:
        self.command = Command()

    def test_discord_webhook_url_미설정시_건너뜀(self) -> None:
        source = NoticeSource.objects.create(
            name='테스트 소스',
            url='https://example.com',
            crawler_type='dacon',
            discord_webhook_url='',
            is_active=True,
        )
        discord = MagicMock()

        with patch(
            'apps.notifications.management.commands.check_new_notices.get_crawler',
        ) as mock_get_crawler:
            self.command._process_source(source, discord)

        mock_get_crawler.assert_not_called()
        discord.send_notice.assert_not_called()

    @patch('apps.notifications.management.commands.check_new_notices.time.sleep')
    def test_신규_공지_발견시_discord_send_notice_호출_및_is_notified_갱신(self, mock_sleep) -> None:
        source = NoticeSource.objects.create(
            name='테스트 소스',
            url='https://example.com',
            crawler_type='dacon',
            discord_webhook_url='https://discord.com/api/webhooks/1/a',
            is_active=True,
        )
        item = DaconItem(
            article_id='1', title='신규 대회', url='https://dacon.io/x',
            status=None, participant_count=None, tags=[],
        )
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = [item]
        mock_crawler.crawl_detail.return_value = None
        discord = MagicMock()
        discord.send_notice.return_value = True

        with patch(
            'apps.notifications.management.commands.check_new_notices.get_crawler',
            return_value=mock_crawler,
        ):
            self.command._process_source(source, discord)

        discord.send_notice.assert_called_once_with(
            'https://discord.com/api/webhooks/1/a', source, item,
        )
        notice = Notice.objects.get(source=source, article_id='1')
        self.assertTrue(notice.is_notified)
        self.assertIsNotNone(notice.notified_at)
        mock_sleep.assert_called_once()
