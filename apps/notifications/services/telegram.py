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
        except requests.HTTPError as e:
            # HTTPError 메시지 자체에 봇 토큰이 포함된 URL이 그대로 들어간다(requests가
            # 'for url: https://api.telegram.org/bot<TOKEN>/...' 형태로 채움)—
            # 예외를 그대로 로깅하지 않고 상태 코드만 남긴다
            status = e.response.status_code if e.response is not None else '?'
            logger.error('텔레그램 메시지 발송 실패 (chat_id=%s, status=%s)', chat_id, status)
            return False
        except requests.RequestException as e:
            # ConnectionError 등 다른 예외 메시지에도 토큰이 포함된 URL 경로가 섞일 수 있으므로
            # (예: "Max retries exceeded with url: ...") 예외 원문 대신 타입명만 남긴다
            logger.error(
                '텔레그램 메시지 발송 실패 (chat_id=%s, error_type=%s)', chat_id, type(e).__name__,
            )
            return False
