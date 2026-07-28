import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_TELEGRAM_API = 'https://api.telegram.org/bot{token}/sendMessage'
_REQUEST_TIMEOUT = 10


class TelegramService:
    """Telegram Bot API를 이용한 관리자 알림 발송 서비스"""

    def __init__(self) -> None:
        self._token: str = settings.TELEGRAM_BOT_TOKEN

    def send_admin_alert(self, message: str) -> bool:
        """댓글·좋아요 등 사이트 이벤트를 관리자 채팅방으로 발송한다."""
        chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
        if not chat_id:
            logger.warning('TELEGRAM_ADMIN_CHAT_ID 미설정 — 관리자 알림을 건너뜁니다.')
            return False
        return self._send(message, chat_id)

    def _send(self, text: str, chat_id: str) -> bool:
        url = _TELEGRAM_API.format(token=self._token)
        payload = {
            'chat_id': chat_id,
            'text': text,
            'disable_web_page_preview': False,
        }
        try:
            response = requests.post(url, json=payload, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error('텔레그램 메시지 발송 실패 (chat_id=%s): %s', chat_id, e)
            return False
