import logging
from datetime import date

import requests

from apps.clubs.models import RecruitmentDetection

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 10


class ClubDiscordService:
    """동아리 모집 오픈/실패 알림용 Discord Webhook 발송 서비스"""

    def send_recruitment_alert(self, webhook_url: str, club_name: str, detection: RecruitmentDetection) -> bool:
        """새로 열린 모집 알림을 발송한다. 성공 여부를 반환한다."""
        period = self._format_period(detection.application_start, detection.application_end)
        lines = [
            '📣 동아리 모집이 시작됐습니다!',
            f'**{club_name}**',
            f'🗓️ {period}',
        ]
        if detection.apply_url:
            lines.append(f'🔗 {detection.apply_url}')
        return self._send('\n'.join(lines), webhook_url)

    def send_failure_alert(self, webhook_url: str, club_name: str) -> bool:
        """연속 실패 임계치 도달 시 경고 알림을 발송한다."""
        message = (
            f'⚠️ 감시 상태 이상\n**{club_name}** 홈페이지 확인이 5회 연속 실패했습니다. '
            '사이트 구조 변경이나 접근 차단 가능성이 있으니 확인이 필요합니다.'
        )
        return self._send(message, webhook_url)

    def _format_period(self, start: date | None, end: date | None) -> str:
        if start and end:
            return f'{start:%Y-%m-%d} ~ {end:%Y-%m-%d}'
        if start:
            return f'{start:%Y-%m-%d} ~'
        if end:
            return f'~ {end:%Y-%m-%d}'
        return '지원 기간 미확인'

    def _send(self, content: str, webhook_url: str) -> bool:
        payload = {
            'content': content,
            # 동아리명에 @everyone/@here 등이 섞여 있어도 실제 멘션이 발생하지 않도록 차단
            'allowed_mentions': {'parse': []},
        }
        try:
            # 리디렉션을 따라가지 않는다 — 저장된 웹훅 URL이 모델 검증을 우회해 다른 호스트를
            # 가리키더라도, 그 호스트가 임의의 내부/외부 주소로 리디렉션시켜 서버가 그 주소에
            # 요청을 보내는 SSRF 경로를 추가로 차단한다.
            response = requests.post(webhook_url, json=payload, timeout=_REQUEST_TIMEOUT, allow_redirects=False)
            response.raise_for_status()
            return True
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else '?'
            logger.error('디스코드 메시지 발송 실패 (status=%s)', status)
            return False
        except requests.RequestException as e:
            logger.error('디스코드 메시지 발송 실패 (error_type=%s)', type(e).__name__)
            return False
