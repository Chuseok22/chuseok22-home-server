import logging
from datetime import date, datetime

import requests
from django.utils import timezone

from apps.notifications.crawlers.base import BaseNoticeItem
from apps.notifications.crawlers.dacon import DaconItem
from apps.notifications.crawlers.linkareer import ContestItem
from apps.notifications.crawlers.sejong import SejongNoticeItem
from apps.notifications.crawlers.sejong_do import SejongDoItem
from apps.notifications.models import NoticeSource

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 10
# Discord 메시지 content 필드의 최대 길이는 2000자다. 정확히 2000에 맞추면 이모지 등
# Python len()과 Discord 측 계산 기준이 한 글자라도 어긋날 때 다시 400을 받을 수 있으므로
# 여유를 두고, 초과 시 400 응답으로 발송 자체가 실패해 is_notified가 갱신되지 않고
# 매 실행마다 재시도되는 것을 막기 위해 이 길이로 자른다.
_MAX_CONTENT_LENGTH = 1900


class DiscordService:
    """Discord Webhook을 이용한 공지 알림 발송 서비스"""

    def send_notice(self, webhook_url: str, source: NoticeSource, item: BaseNoticeItem) -> bool:
        """공지사항 알림 메시지를 발송한다. 성공 여부를 반환한다."""
        message = self._format_message(source, item)
        return self._send(message, webhook_url, source.name)

    def _format_message(self, source: NoticeSource, item: BaseNoticeItem) -> str:
        if isinstance(item, SejongNoticeItem):
            return self._format_sejong_notice(source, item)
        if isinstance(item, SejongDoItem):
            return self._format_sejong_do(source, item)
        if isinstance(item, ContestItem):
            return self._format_contest(source, item)
        if isinstance(item, DaconItem):
            return self._format_dacon(source, item)
        return f'🔔 새 알림\n**[{source.name}]**\n📌 {item.title}\n🔗 {item.url}'

    def _format_sejong_notice(self, source: NoticeSource, item: SejongNoticeItem) -> str:
        lines = [
            '🔔 새 공지사항 알림\n',
            f'**[{source.name}]**',
            f'📌 {item.title}',
        ]
        if item.published_at:
            lines.append(f'📅 {item.published_at.strftime("%Y.%m.%d")}')
        lines.append(f'🔗 {item.url}')
        return '\n'.join(lines)

    def _format_sejong_do(self, source: NoticeSource, item: SejongDoItem) -> str:
        lines = [
            '🔔 두드림 비교과 알림\n',
            f'**[{source.name}]**',
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
            f'**[{source.name}]**',
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

    def _format_dacon(self, source: NoticeSource, item: DaconItem) -> str:
        lines = [
            '🎯 새 데이터 경진대회 알림\n',
            f'**[{source.name}]**',
            f'📌 {item.title}',
        ]
        if item.status:
            lines.append(f'📋 상태: {item.status}')
        if item.participant_count is not None:
            lines.append(f'👥 참가자: {item.participant_count}명')
        if item.tags:
            lines.append(f'📂 태그: {", ".join(item.tags)}')
        lines.append(f'🔗 {item.url}')
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

    def _send(self, content: str, webhook_url: str, source_name: str) -> bool:
        if len(content) > _MAX_CONTENT_LENGTH:
            logger.warning(
                '디스코드 메시지가 %d자를 초과해 링크 줄은 보존한 채 잘랐습니다 (source=%s)',
                _MAX_CONTENT_LENGTH, source_name,
            )
            content = self._truncate_preserving_last_line(content)
        payload = {
            'content': content,
            # 크롤링한 제목에 @everyone/@here/역할 멘션이 섞여 있어도 실제 멘션이 발생하지 않도록 차단
            'allowed_mentions': {'parse': []},
        }
        try:
            response = requests.post(webhook_url, json=payload, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            return True
        except requests.HTTPError as e:
            # HTTPError 메시지 자체에 webhook_url이 포함되므로(requests가 'for url: ...' 형태로
            # 채움) 예외를 그대로 로깅하지 않고 상태 코드만 남긴다
            status = e.response.status_code if e.response is not None else '?'
            logger.error('디스코드 메시지 발송 실패 (source=%s, status=%s)', source_name, status)
            return False
        except requests.RequestException as e:
            # ConnectionError 등 다른 예외 메시지에도 webhook_url 경로가 섞일 수 있으므로
            # (예: "Max retries exceeded with url: ...") 예외 원문 대신 타입명만 남긴다
            logger.error(
                '디스코드 메시지 발송 실패 (source=%s, error_type=%s)', source_name, type(e).__name__,
            )
            return False

    def _truncate_preserving_last_line(self, content: str) -> str:
        """content가 너무 길면 마지막 줄(공지 링크)은 유지한 채 앞부분만 줄인다."""
        body, _, url_line = content.rpartition('\n')
        reserved = len(url_line) + len('\n…\n')
        truncated_body = body[: max(_MAX_CONTENT_LENGTH - reserved, 0)]
        return f'{truncated_body}\n…\n{url_line}'
