from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase
from django.utils import timezone

from apps.notifications.crawlers.base import BaseNoticeItem
from apps.notifications.crawlers.dacon import DaconItem
from apps.notifications.crawlers.dreamspon import DreamsponItem
from apps.notifications.crawlers.linkareer import ContestItem
from apps.notifications.crawlers.sejong import SejongNoticeItem
from apps.notifications.crawlers.sejong_do import SejongDoItem
from apps.notifications.models import NoticeSource
from apps.notifications.services.discord import DiscordService

_WEBHOOK_URL = 'https://discord.com/api/webhooks/123/test-token'


class TestDiscordServiceFormatMessage(TestCase):
    def setUp(self) -> None:
        self.service = DiscordService()
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
        self.assertIn('**[테스트 출처]**', result)
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

    def test_dacon_포맷(self) -> None:
        item = DaconItem(
            article_id='236727',
            title='제3회 풍력발전량 예측 AI 경진대회',
            url='https://dacon.io/competitions/official/236727/overview/',
            status='참가신청중',
            participant_count=1305,
            tags=['알고리즘', '에너지'],
        )
        result = self.service._format_message(self.source, item)
        self.assertIn('새 데이터 경진대회 알림', result)
        self.assertIn('제3회 풍력발전량 예측 AI 경진대회', result)
        self.assertIn('참가신청중', result)
        self.assertIn('1305명', result)
        self.assertIn('알고리즘, 에너지', result)
        self.assertIn('https://dacon.io/competitions/official/236727/overview/', result)

    def test_dreamspon_포맷(self) -> None:
        item = DreamsponItem(
            article_id='9130',
            title='에디티지 신진 연구자 대상 에디티지 장학',
            url='https://www.dreamspon.com/scholarship/view.html?idx=9130',
            organization='에디티지',
            hit_count=1294,
            scholarship_type='포상/상금',
            target='이공계열 신진 연구자',
            recruit_count='총 16명',
            benefit='최대 1,000만원',
            application_start=date(2026, 5, 26),
            application_end=date(2026, 8, 7),
            tags=['#장학프로그램', '#기타지원'],
        )
        result = self.service._format_message(self.source, item)
        self.assertIn('새 장학금 알림', result)
        self.assertIn('에디티지 신진 연구자 대상 에디티지 장학', result)
        self.assertIn('에디티지', result)
        self.assertIn('🏷 장학종류: 포상/상금', result)
        self.assertIn('이공계열 신진 연구자', result)
        self.assertIn('총 16명', result)
        self.assertIn('최대 1,000만원', result)
        self.assertIn('📋 신청기간: 2026.05.26 ~ 2026.08.07', result)
        self.assertIn('#장학프로그램, #기타지원', result)
        self.assertIn('https://www.dreamspon.com/scholarship/view.html?idx=9130', result)

    def test_dreamspon_마스킹_필드는_알림에_노출되지_않음(self) -> None:
        # 비로그인/로그인 실패 시 크롤러가 마스킹 필드를 None으로 채운 아이템을 넘기더라도
        # Discord 메시지에 '*' 마스킹 문자열이 섞여나가지 않아야 한다
        item = DreamsponItem(
            article_id='9130',
            title='에디티지 신진 연구자 대상 에디티지 장학',
            url='https://www.dreamspon.com/scholarship/view.html?idx=9130',
            organization='에디티지',
            hit_count=None,
            scholarship_type=None,
            target=None,
            recruit_count=None,
            benefit=None,
            application_start=None,
            application_end=None,
            tags=[],
        )
        result = self.service._format_message(self.source, item)
        # 마스킹 문자열(예: '*****')은 연속된 3개 이상의 '*'로 나타나며,
        # 메시지 서식용 '**bold**' 마크다운(연속 2개)과는 구분된다
        self.assertNotRegex(result, r'\*{3,}')

    def test_unknown_item_fallback(self) -> None:
        item = BaseNoticeItem(article_id='x', title='임시 제목', url='https://example.com')
        result = self.service._format_message(self.source, item)
        self.assertIn('임시 제목', result)
        self.assertIn('https://example.com', result)


class TestDiscordServiceDday(TestCase):
    def setUp(self) -> None:
        self.service = DiscordService()

    def test_dday_미래(self) -> None:
        future = timezone.localdate() + timedelta(days=5)
        result = self.service._dday_date(future)
        self.assertEqual(result, ' (D-5)')

    def test_dday_오늘(self) -> None:
        result = self.service._dday_date(timezone.localdate())
        self.assertEqual(result, ' (D-Day)')

    def test_dday_과거(self) -> None:
        past = timezone.localdate() - timedelta(days=3)
        result = self.service._dday_date(past)
        self.assertEqual(result, ' (D+3)')


class TestDiscordServiceSendNotice(TestCase):
    def setUp(self) -> None:
        self.service = DiscordService()
        self.source = MagicMock(spec=NoticeSource)
        self.source.name = '테스트 출처'
        self.item = SejongNoticeItem(
            article_id='1', title='공지', url='https://example.com', published_at=None,
        )

    def test_send_notice_성공(self) -> None:
        with patch('apps.notifications.services.discord.requests.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            result = self.service.send_notice(_WEBHOOK_URL, self.source, self.item)

        self.assertTrue(result)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.args[0], _WEBHOOK_URL)
        called_json = mock_post.call_args.kwargs['json']
        self.assertIn('https://example.com', called_json['content'])

    def test_send_notice_실패(self) -> None:
        with patch('apps.notifications.services.discord.requests.post') as mock_post:
            mock_post.side_effect = requests.RequestException('boom')
            result = self.service.send_notice(_WEBHOOK_URL, self.source, self.item)

        self.assertFalse(result)

    def test_send_notice_allowed_mentions으로_전체_멘션을_차단한다(self) -> None:
        """크롤링한 공지 제목에 @everyone 등이 섞여 있어도 실제로 멘션되지 않도록 방지한다."""
        with patch('apps.notifications.services.discord.requests.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            self.service.send_notice(_WEBHOOK_URL, self.source, self.item)

        called_json = mock_post.call_args.kwargs['json']
        self.assertEqual(called_json['allowed_mentions'], {'parse': []})

    def test_send_notice_긴_내용은_링크_줄을_보존한_채_잘린다(self) -> None:
        long_item = SejongNoticeItem(
            article_id='1', title='제' * 2500, url='https://example.com/notice/1', published_at=None,
        )
        with patch('apps.notifications.services.discord.requests.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            self.service.send_notice(_WEBHOOK_URL, self.source, long_item)

        sent_content = mock_post.call_args.kwargs['json']['content']
        self.assertLessEqual(len(sent_content), 1900)
        # 잘리더라도 알림의 핵심인 공지 링크(마지막 줄)는 항상 보존되어야 한다
        self.assertTrue(sent_content.endswith('https://example.com/notice/1'))

    def test_send_notice_http_에러시_webhook_url을_로그에_남기지_않는다(self) -> None:
        """HTTPError 메시지 자체에 webhook_url(=시크릿)이 포함되므로(requests가 'for url: ...'
        형태로 채움) 예외 메시지를 그대로 로깅하지 않고 상태 코드만 남겨야 한다."""
        response = requests.Response()
        response.status_code = 400
        response.url = _WEBHOOK_URL
        http_error = requests.HTTPError(
            f'400 Client Error: Bad Request for url: {_WEBHOOK_URL}', response=response,
        )
        with patch('apps.notifications.services.discord.requests.post') as mock_post:
            mock_post.return_value.raise_for_status.side_effect = http_error
            with self.assertLogs('apps.notifications.services.discord', level='ERROR') as captured:
                result = self.service.send_notice(_WEBHOOK_URL, self.source, self.item)

        self.assertFalse(result)
        self.assertNotIn('test-token', captured.output[0])
        self.assertIn('테스트 출처', captured.output[0])
        self.assertIn('400', captured.output[0])

    def test_send_notice_연결_실패시_webhook_url을_로그에_남기지_않는다(self) -> None:
        """ConnectionError 메시지에도 webhook_url 경로가 포함될 수 있으므로 동일하게 방어한다."""
        with patch('apps.notifications.services.discord.requests.post') as mock_post:
            mock_post.side_effect = requests.ConnectionError(
                'Max retries exceeded with url: /api/webhooks/123/test-token (Caused by ...)',
            )
            with self.assertLogs('apps.notifications.services.discord', level='ERROR') as captured:
                result = self.service.send_notice(_WEBHOOK_URL, self.source, self.item)

        self.assertFalse(result)
        self.assertNotIn('test-token', captured.output[0])
        self.assertIn('테스트 출처', captured.output[0])
