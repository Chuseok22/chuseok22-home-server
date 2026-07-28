from unittest.mock import patch

import requests
from django.test import TestCase, override_settings

from apps.notifications.services.telegram import TelegramService


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


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_ADMIN_CHAT_ID='')
class TestTelegramServiceSendAdminAlertMissingChatId(TestCase):
    def test_admin_chat_id_미설정시_건너뜀(self) -> None:
        service = TelegramService()

        with patch('apps.notifications.services.telegram.requests.post') as mock_post:
            result = service.send_admin_alert('새 댓글이 달렸습니다.')

        assert result is False
        mock_post.assert_not_called()


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_ADMIN_CHAT_ID='admin-chat-id')
class TestTelegramServiceSendAdminAlertLogSafety(TestCase):
    def test_http_에러시_봇_토큰을_로그에_남기지_않는다(self) -> None:
        """HTTPError 메시지 자체에 봇 토큰이 포함된 URL이 들어가므로(requests가
        'for url: https://api.telegram.org/bot<TOKEN>/...' 형태로 채움) 예외 메시지를
        그대로 로깅하지 않고 상태 코드만 남겨야 한다."""
        service = TelegramService()
        response = requests.Response()
        response.status_code = 400
        http_error = requests.HTTPError(
            '400 Client Error: Bad Request for url: '
            'https://api.telegram.org/bottest-token/sendMessage',
            response=response,
        )

        with patch('apps.notifications.services.telegram.requests.post') as mock_post:
            mock_post.return_value.raise_for_status.side_effect = http_error
            with self.assertLogs('apps.notifications.services.telegram', level='ERROR') as captured:
                result = service.send_admin_alert('새 댓글이 달렸습니다.')

        assert result is False
        self.assertNotIn('test-token', captured.output[0])
        self.assertIn('admin-chat-id', captured.output[0])
        self.assertIn('400', captured.output[0])

    def test_연결_실패시_봇_토큰을_로그에_남기지_않는다(self) -> None:
        """ConnectionError 메시지에도 토큰이 포함된 URL 경로가 섞일 수 있으므로 동일하게 방어한다."""
        service = TelegramService()

        with patch('apps.notifications.services.telegram.requests.post') as mock_post:
            mock_post.side_effect = requests.ConnectionError(
                'Max retries exceeded with url: /bottest-token/sendMessage (Caused by ...)',
            )
            with self.assertLogs('apps.notifications.services.telegram', level='ERROR') as captured:
                result = service.send_admin_alert('새 댓글이 달렸습니다.')

        assert result is False
        self.assertNotIn('test-token', captured.output[0])
        self.assertIn('admin-chat-id', captured.output[0])
