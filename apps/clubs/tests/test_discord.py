from datetime import date
from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, TestCase

from apps.clubs.models import RecruitmentDetection, TrackedClub
from apps.clubs.services.discord import ClubDiscordService


class TestSendRecruitmentAlert(TestCase):
    def setUp(self) -> None:
        self.club = TrackedClub.objects.create(name='SOPT', homepage_url='https://www.sopt.org/')
        self.service = ClubDiscordService()

    @patch('apps.clubs.services.discord.requests.post')
    def test_지원기간이_있으면_메시지에_포함한다(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        detection = RecruitmentDetection.objects.create(
            tracked_club=self.club,
            application_start=date(2026, 9, 1), application_end=date(2026, 9, 14),
            apply_url='https://www.sopt.org/apply', evidence_quote='근거 문장',
        )

        result = self.service.send_recruitment_alert(
            'https://discord.com/api/webhooks/1/a', 'SOPT', detection,
        )

        assert result is True
        sent_content = mock_post.call_args.kwargs['json']['content']
        assert 'SOPT' in sent_content
        assert '2026-09-01 ~ 2026-09-14' in sent_content
        assert 'https://www.sopt.org/apply' in sent_content
        assert mock_post.call_args.kwargs['json']['allowed_mentions'] == {'parse': []}
        assert mock_post.call_args.kwargs['allow_redirects'] is False

    @patch('apps.clubs.services.discord.requests.post')
    def test_지원기간이_없으면_미확인_문구를_사용한다(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        detection = RecruitmentDetection.objects.create(
            tracked_club=self.club, evidence_quote='근거 문장',
        )

        self.service.send_recruitment_alert('https://discord.com/api/webhooks/1/a', 'SOPT', detection)

        sent_content = mock_post.call_args.kwargs['json']['content']
        assert '지원 기간 미확인' in sent_content


class TestSendFailureAlert(SimpleTestCase):
    @patch('apps.clubs.services.discord.requests.post')
    def test_경고_메시지를_발송한다(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        service = ClubDiscordService()

        result = service.send_failure_alert('https://discord.com/api/webhooks/1/a', 'SOPT')

        assert result is True
        sent_content = mock_post.call_args.kwargs['json']['content']
        assert 'SOPT' in sent_content
        assert '5회 연속 실패' in sent_content

    @patch('apps.clubs.services.discord.requests.post')
    def test_HTTP_오류시_False를_반환한다(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        service = ClubDiscordService()

        assert service.send_failure_alert('https://discord.com/api/webhooks/1/a', 'SOPT') is False
