from datetime import date, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.notifications.crawlers.linkareer import ContestItem
from apps.notifications.crawlers.sejong import SejongNoticeItem
from apps.notifications.crawlers.sejong_do import SejongDoItem
from apps.notifications.models import NoticeSource
from apps.notifications.services.telegram import TelegramService


@override_settings(TELEGRAM_BOT_TOKEN='test-token')
class TestTelegramServiceFormatMessage(TestCase):
    def setUp(self) -> None:
        self.service = TelegramService()
        self.source = MagicMock(spec=NoticeSource)
        self.source.name = '테스트 출처'

    def test_sejong_notice_포맷(self) -> None:
        item = SejongNoticeItem(
            article_id='1',
            title='공지 제목',
            url='https://example.com',
            published_at=date(2025, 6, 16),
        )
        result = self.service._format_message(self.source, item)
        self.assertIn('새 공지사항 알림', result)
        self.assertIn('공지 제목', result)
        self.assertIn('2025.06.16', result)
        self.assertIn('https://example.com', result)

    def test_sejong_do_포맷_organizer_포함(self) -> None:
        item = SejongDoItem(
            article_id='2',
            title='두드림 프로그램',
            url='https://do.sejong.ac.kr/activity/1',
            organizer='세종대학교',
            application_start=datetime(2025, 6, 1, 9, 0),
            application_end=datetime(2025, 6, 30, 18, 0),
            operation_start=datetime(2025, 7, 1, 9, 0),
            operation_end=datetime(2025, 7, 31, 18, 0),
        )
        result = self.service._format_message(self.source, item)
        self.assertIn('두드림 비교과 알림', result)
        self.assertIn('세종대학교', result)
        self.assertIn('신청:', result)
        self.assertIn('운영:', result)

    def test_contest_포맷(self) -> None:
        item = ContestItem(
            article_id='311551',
            title='공모전 제목',
            url='https://linkareer.com/activity/311551',
            company_type='대기업',
            target='대학생',
            prize='1000만원',
            application_start=date(2025, 6, 1),
            application_end=date(2025, 6, 30),
            homepage='https://company.com',
            benefit='장학금',
            categories=['디자인', 'IT/개발'],
        )
        result = self.service._format_message(self.source, item)
        self.assertIn('공모전 알림', result)
        self.assertIn('대기업', result)
        self.assertIn('대학생', result)
        self.assertIn('1000만원', result)
        self.assertIn('디자인, IT/개발', result)
        self.assertIn('https://company.com', result)
        self.assertIn('링커리어', result)

    def test_unknown_item_fallback(self) -> None:
        from apps.notifications.crawlers.base import BaseNoticeItem
        item = BaseNoticeItem(
            article_id='x',
            title='임시 제목',
            url='https://example.com',
        )
        result = self.service._format_message(self.source, item)
        self.assertIn('임시 제목', result)
        self.assertIn('https://example.com', result)


@override_settings(TELEGRAM_BOT_TOKEN='test-token')
class TestTelegramServiceDday(TestCase):
    def setUp(self) -> None:
        self.service = TelegramService()

    def test_dday_미래(self) -> None:
        from datetime import timedelta
        from django.utils import timezone
        future = timezone.localdate() + timedelta(days=5)
        result = self.service._dday_date(future)
        self.assertEqual(result, ' (D-5)')

    def test_dday_오늘(self) -> None:
        from django.utils import timezone
        result = self.service._dday_date(timezone.localdate())
        self.assertEqual(result, ' (D-Day)')

    def test_dday_과거(self) -> None:
        from datetime import timedelta
        from django.utils import timezone
        past = timezone.localdate() - timedelta(days=3)
        result = self.service._dday_date(past)
        self.assertEqual(result, ' (D+3)')


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_ADMIN_CHAT_ID='admin-chat-id')
class TestTelegramServiceSendAdminAlert(TestCase):
    def test_send_admin_alert_성공(self) -> None:
        service = TelegramService()

        with patch('apps.notifications.services.telegram.requests.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            result = service.send_admin_alert('새 댓글이 달렸습니다.')

        assert result is True
        mock_post.assert_called_once()
        called_payload = mock_post.call_args.kwargs['json']
        assert called_payload['chat_id'] == 'admin-chat-id'
        assert called_payload['text'] == '새 댓글이 달렸습니다.'
