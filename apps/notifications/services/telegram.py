import logging
from datetime import date

import requests
from django.conf import settings

from apps.notifications.crawlers.base import NoticeItem
from apps.notifications.models import Notice, NoticeSource

logger = logging.getLogger(__name__)

_TELEGRAM_API = 'https://api.telegram.org/bot{token}/sendMessage'
_REQUEST_TIMEOUT = 10


class TelegramService:
    """Telegram Bot API를 이용한 알림 발송 서비스"""

    def __init__(self) -> None:
        self._token: str = settings.TELEGRAM_BOT_TOKEN
        self._chat_id: str = settings.TELEGRAM_CHAT_ID

    def send_notice(self, source: NoticeSource, notice: Notice, item: NoticeItem | None = None) -> bool:
        """공지사항 알림 메시지를 발송한다. 성공 여부를 반환한다."""
        message = self._format_message(source, notice, item)
        return self._send(message)

    def _format_message(self, source: NoticeSource, notice: Notice, item: NoticeItem | None = None) -> str:
        lines = [
            '🔔 새 공지사항 알림\n',
            f'[{source.name}]',
            f'📌 {notice.title}',
        ]

        if item and (item.application_start or item.application_end):
            lines.append(f'📋 신청: {self._fmt_period(item.application_start, item.application_end)}')

        if item and (item.published_at or item.operation_end):
            op_str = self._fmt_period(item.published_at, item.operation_end)
            dday = self._dday(item.published_at)
            lines.append(f'🗓 운영: {op_str}{dday}')
        elif notice.published_at:
            lines.append(f'📅 {notice.published_at.strftime("%Y.%m.%d")}')

        lines.append(f'🔗 {notice.url}')
        return '\n'.join(lines)

    def _fmt_period(self, start: date | None, end: date | None) -> str:
        s = start.strftime('%Y.%m.%d') if start else '?'
        e = end.strftime('%Y.%m.%d') if end else '?'
        return f'{s} ~ {e}'

    def _dday(self, target: date | None) -> str:
        if not target:
            return ''
        from django.utils import timezone
        delta = (target - timezone.localdate()).days
        if delta > 0:
            return f' (D-{delta})'
        if delta == 0:
            return ' (D-Day)'
        return f' (D+{abs(delta)})'

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
