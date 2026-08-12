from datetime import date
from unittest.mock import MagicMock, patch

import requests

from apps.cinema.services.discord import CinemaDiscordService

_WEBHOOK_URL = 'https://discord.com/api/webhooks/123/test-token'


class TestSendNewDateAlert:
    @patch('apps.cinema.services.discord.requests.post')
    def test_새_날짜_알림_메시지에_필요한_정보가_모두_포함된다(self, mock_post) -> None:
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        service = CinemaDiscordService()

        result = service.send_new_date_alert(
            webhook_url=_WEBHOOK_URL,
            cinema_screen_label='CGV 용산아이파크몰 IMAX',
            movie_title='스파이더맨: 브랜드 뉴 데이',
            show_date=date(2026, 9, 5),
            showtimes=['10:30', '15:00'],
            booking_url='https://cgv.co.kr/cnm/movieBook/cinema?siteNo=0013',
        )

        assert result is True
        sent_content = mock_post.call_args.kwargs['json']['content']
        assert 'CGV 용산아이파크몰 IMAX' in sent_content
        assert '스파이더맨: 브랜드 뉴 데이' in sent_content
        assert '2026-09-05' in sent_content
        assert '토' in sent_content
        assert '10:30 / 15:00' in sent_content
        assert 'https://cgv.co.kr/cnm/movieBook/cinema?siteNo=0013' in sent_content

    @patch('apps.cinema.services.discord.requests.post')
    def test_발송_실패시_False를_반환한다(self, mock_post) -> None:
        mock_post.side_effect = requests.ConnectionError('boom')
        service = CinemaDiscordService()

        result = service.send_new_date_alert(
            webhook_url=_WEBHOOK_URL, cinema_screen_label='테스트', movie_title='테스트',
            show_date=date(2026, 9, 5), showtimes=['10:00'], booking_url='https://example.com',
        )

        assert result is False


class TestSendFailureAlert:
    @patch('apps.cinema.services.discord.requests.post')
    def test_전달된_모든_웹훅에_경고_메시지를_보낸다(self, mock_post) -> None:
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        service = CinemaDiscordService()

        result = service.send_failure_alert(
            [_WEBHOOK_URL, 'https://discord.com/api/webhooks/999/other'], 'CGV 용산아이파크몰 IMAX',
        )

        assert result is True
        assert mock_post.call_count == 2
        first_content = mock_post.call_args_list[0].kwargs['json']['content']
        assert '5회 연속' in first_content
        assert 'CGV 용산아이파크몰 IMAX' in first_content

    @patch('apps.cinema.services.discord.requests.post')
    def test_일부_웹훅만_실패해도_모든_웹훅을_시도하고_False를_반환한다(self, mock_post) -> None:
        ok_response = MagicMock(raise_for_status=lambda: None)

        def _side_effect(url, **kwargs):
            if url == _WEBHOOK_URL:
                raise requests.ConnectionError('boom')
            return ok_response

        mock_post.side_effect = _side_effect
        service = CinemaDiscordService()

        result = service.send_failure_alert(
            [_WEBHOOK_URL, 'https://discord.com/api/webhooks/999/other'], 'CGV 용산아이파크몰 IMAX',
        )

        assert result is False
        assert mock_post.call_count == 2

    @patch('apps.cinema.services.discord.requests.post')
    def test_리디렉션을_따라가지_않는다(self, mock_post) -> None:
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        service = CinemaDiscordService()

        service.send_new_date_alert(
            webhook_url=_WEBHOOK_URL, cinema_screen_label='테스트', movie_title='테스트',
            show_date=date(2026, 9, 5), showtimes=['10:00'], booking_url='https://example.com',
        )

        assert mock_post.call_args.kwargs['allow_redirects'] is False
