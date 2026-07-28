from unittest.mock import patch

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
