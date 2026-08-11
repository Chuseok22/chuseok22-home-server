import logging
from datetime import date

import requests

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 10
_WEEKDAY_LABELS = ['월', '화', '수', '목', '금', '토', '일']


class CinemaDiscordService:
    """영화 예매 오픈/실패 알림용 Discord Webhook 발송 서비스"""

    def send_new_date_alert(
        self,
        webhook_url: str,
        cinema_screen_label: str,
        movie_title: str,
        show_date: date,
        showtimes: list[str],
        booking_url: str,
    ) -> bool:
        """새로 열린 상영일 알림을 발송한다. 성공 여부를 반환한다."""
        weekday_label = _WEEKDAY_LABELS[show_date.weekday()]
        lines = [
            '🎬 새 날짜 예매 오픈!',
            f'**[{cinema_screen_label}]**',
            f'📌 {movie_title}',
            f'📅 {show_date.strftime("%Y-%m-%d")}({weekday_label})',
            f'🕐 {" / ".join(showtimes)}',
            f'🔗 {booking_url}',
        ]
        return self._send('\n'.join(lines), webhook_url)

    def send_failure_alert(self, webhook_urls: list[str], cinema_screen_label: str) -> None:
        """연속 실패 임계치 도달 시 경고 알림을 대상 웹훅 전체에 1회씩 발송한다."""
        message = (
            f'⚠️ 감시 상태 이상\n**[{cinema_screen_label}]** 크롤링이 5회 연속 실패했습니다. '
            '사이트 구조 변경이나 접근 차단 가능성이 있으니 확인이 필요합니다.'
        )
        for webhook_url in webhook_urls:
            self._send(message, webhook_url)

    def _send(self, content: str, webhook_url: str) -> bool:
        payload = {
            'content': content,
            # 영화 제목에 @everyone/@here 등이 섞여 있어도 실제 멘션이 발생하지 않도록 차단
            'allowed_mentions': {'parse': []},
        }
        try:
            response = requests.post(webhook_url, json=payload, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            return True
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else '?'
            logger.error('디스코드 메시지 발송 실패 (status=%s)', status)
            return False
        except requests.RequestException as e:
            logger.error('디스코드 메시지 발송 실패 (error_type=%s)', type(e).__name__)
            return False
