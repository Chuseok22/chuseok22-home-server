import logging

import requests
from django.conf import settings

from apps.notifications.models import Notice, NoticeSource

logger = logging.getLogger(__name__)

_TELEGRAM_API = 'https://api.telegram.org/bot{token}/sendMessage'
_REQUEST_TIMEOUT = 10


class TelegramService:
    """Telegram Bot API를 이용한 알림 발송 서비스"""

    def __init__(self) -> None:
        self._token: str = settings.TELEGRAM_BOT_TOKEN
        self._chat_id: str = settings.TELEGRAM_CHAT_ID

    def send_notice(self, source: NoticeSource, notice: Notice) -> bool:
        """공지사항 알림 메시지를 발송한다. 성공 여부를 반환한다."""
        message = self._format_message(source, notice)
        return self._send(message)

    def _format_message(self, source: NoticeSource, notice: Notice) -> str:
        date_str = notice.published_at.strftime('%Y.%m.%d') if notice.published_at else '날짜 없음'
        return (
            f'🔔 새 공지사항 알림\n\n'
            f'[{source.name}]\n'
            f'📌 {notice.title}\n'
            f'📅 {date_str}\n'
            f'🔗 {notice.url}'
        )

    def _send(self, text: str) -> bool:
        url = _TELEGRAM_API.format(token=self._token)
        payload = {
            'chat_id': self._chat_id,
            'text': text,
            'disable_web_page_preview': False,
        }
        try:
            response = requests.post(url, json=payload, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error('텔레그램 메시지 발송 실패: %s', e)
            return False
