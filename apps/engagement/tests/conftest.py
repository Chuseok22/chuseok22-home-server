from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_telegram_admin_alert():
    """engagement 앱 테스트에서 post_save 시그널이 실제 텔레그램 API를 호출하지 않도록 막는다."""
    with patch('apps.notifications.services.telegram.TelegramService.send_admin_alert', return_value=True):
        yield
