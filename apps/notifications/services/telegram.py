import logging
from datetime import date, datetime

import requests
from django.conf import settings
from django.utils import timezone

from apps.notifications.crawlers.base import BaseNoticeItem
from apps.notifications.crawlers.linkareer import ContestItem
from apps.notifications.crawlers.sejong import SejongNoticeItem
from apps.notifications.crawlers.sejong_do import SejongDoItem
from apps.notifications.models import NoticeSource

logger = logging.getLogger(__name__)

_TELEGRAM_API = 'https://api.telegram.org/bot{token}/sendMessage'
_REQUEST_TIMEOUT = 10


class TelegramService:
    """Telegram Bot API를 이용한 알림 발송 서비스"""

    def __init__(self) -> None:
        self._token: str = settings.TELEGRAM_BOT_TOKEN

    def send_notice(self, chat_id: str, source: NoticeSource, item: BaseNoticeItem) -> bool:
        """공지사항 알림 메시지를 발송한다. 성공 여부를 반환한다."""
        message = self._format_message(source, item)
        return self._send(message, chat_id)

    def _format_message(self, source: NoticeSource, item: BaseNoticeItem) -> str:
        if isinstance(item, SejongNoticeItem):
            return self._format_sejong_notice(source, item)
        if isinstance(item, SejongDoItem):
            return self._format_sejong_do(source, item)
        if isinstance(item, ContestItem):
            return self._format_contest(source, item)
        return f'🔔 새 알림\n[{source.name}]\n📌 {item.title}\n🔗 {item.url}'

    def _format_sejong_notice(self, source: NoticeSource, item: SejongNoticeItem) -> str:
        lines = [
            '🔔 새 공지사항 알림\n',
            f'[{source.name}]',
            f'📌 {item.title}',
        ]
        if item.published_at:
            lines.append(f'📅 {item.published_at.strftime("%Y.%m.%d")}')
        lines.append(f'🔗 {item.url}')
        return '\n'.join(lines)

    def _format_sejong_do(self, source: NoticeSource, item: SejongDoItem) -> str:
        lines = [
            '🔔 두드림 비교과 알림\n',
            f'[{source.name}]',
            f'📌 {item.title}',
        ]
        if item.organizer:
            lines.append(f'🏢 {item.organizer}')
        if item.application_start or item.application_end:
            lines.append(
                f'📋 신청: {self._fmt_period_dt(item.application_start, item.application_end)}'
                f'{self._dday_dt(item.application_end)}'
            )
        if item.operation_start or item.operation_end:
            lines.append(f'🗓 운영: {self._fmt_period_dt(item.operation_start, item.operation_end)}')
        lines.append(f'🔗 {item.url}')
        return '\n'.join(lines)

    def _format_contest(self, source: NoticeSource, item: ContestItem) -> str:
        lines = [
            '🏆 새 공모전 알림\n',
            f'[{source.name}]',
            f'📌 {item.title}',
        ]
        if item.company_type:
            lines.append(f'🏢 기업형태: {item.company_type}')
        if item.target:
            lines.append(f'👥 참여대상: {item.target}')
        if item.prize:
            lines.append(f'🎁 시상규모: {item.prize}')
        if item.application_start or item.application_end:
            lines.append(
                f'📋 접수기간: {self._fmt_period_date(item.application_start, item.application_end)}'
                f'{self._dday_date(item.application_end)}'
            )
        if item.categories:
            lines.append(f'📂 공모분야: {", ".join(item.categories)}')
        if item.benefit:
            lines.append(f'💰 활동혜택: {item.benefit}')
        if item.homepage:
            lines.append(f'🌐 홈페이지: {item.homepage}')
        lines.append(f'🔗 링커리어: {item.url}')
        return '\n'.join(lines)

    def _fmt_period_dt(self, start: datetime | None, end: datetime | None) -> str:
        s = start.strftime('%Y.%m.%d %H:%M') if start else '?'
        e = end.strftime('%Y.%m.%d %H:%M') if end else '?'
        return f'{s} ~ {e}'

    def _fmt_period_date(self, start: date | None, end: date | None) -> str:
        s = start.strftime('%Y.%m.%d') if start else '?'
        e = end.strftime('%Y.%m.%d') if end else '?'
        return f'{s} ~ {e}'

    def _dday_dt(self, target: datetime | None) -> str:
        if not target:
            return ''
        return self._dday_date(target.date())

    def _dday_date(self, target: date | None) -> str:
        if not target:
            return ''
        delta = (target - timezone.localdate()).days
        if delta > 0:
            return f' (D-{delta})'
        if delta == 0:
            return ' (D-Day)'
        return f' (D+{abs(delta)})'

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
